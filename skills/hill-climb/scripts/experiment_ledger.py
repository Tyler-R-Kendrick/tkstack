"""Durable reservations for one or more bounded local experiments.

The caller owns provider execution and must reserve a provider-enforced upper
bound before dispatch. A timeout cannot prove non-execution. This ledger keeps
uncertain reservations outstanding until usage or non-execution is reported.
"""

import json
from pathlib import Path
import sqlite3
from datetime import datetime, timezone


SCHEMA_VERSION = 1
MAX_INTEGER = (1 << 63) - 1


def _text(value, name):
    if not isinstance(value, str) or not value.strip() or len(value) > 1024 or "\x00" in value:
        raise ValueError(f"{name} must be nonempty text of at most 1024 characters")
    return value


def _number(value, name):
    if type(value) is not int or not 0 <= value <= MAX_INTEGER:
        raise ValueError(f"{name} must be a nonnegative SQLite integer")
    return value


def _now():
    return datetime.now(timezone.utc).isoformat()


class Ledger:
    """SQLite-backed accounting. Methods open independent connections per call.

    An experiment's limits are fixed at initialization. Each run key identifies
    one external dispatch and cannot be reused even after cancellation. Callers
    must invoke the external effect only when dispatch returns
    ``dispatch_granted: True``. A lost dispatch response requires reconciliation,
    not a second launch, even when the first launch may never have started.
    """

    def __init__(self, database):
        self.database = Path(database)

    def _connect(self):
        if not self.database.is_file():
            raise ValueError("Experiment ledger has not been initialized")
        connection = sqlite3.connect(self.database, timeout=30, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        if connection.execute("PRAGMA user_version").fetchone()[0] != SCHEMA_VERSION:
            connection.close()
            raise ValueError("Unsupported experiment ledger schema")
        return connection

    def initialize(self, experiment, *, max_trials, max_tokens):
        experiment = _text(experiment, "experiment")
        max_trials = _number(max_trials, "max_trials")
        max_tokens = _number(max_tokens, "max_tokens")
        self.database.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database, timeout=30, isolation_level=None)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA foreign_keys=ON")
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, SCHEMA_VERSION):
                raise ValueError("Unsupported experiment ledger schema")
            connection.execute("PRAGMA journal_mode=WAL")
            connection.executescript("""
                BEGIN IMMEDIATE;
                CREATE TABLE IF NOT EXISTS experiments (
                    experiment TEXT PRIMARY KEY,
                    max_trials INTEGER NOT NULL,
                    max_tokens INTEGER NOT NULL,
                    overrun INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS runs (
                    experiment TEXT NOT NULL REFERENCES experiments(experiment),
                    run_key TEXT NOT NULL,
                    reserved_tokens INTEGER NOT NULL,
                    trial_units INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    actual_tokens INTEGER,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (experiment, run_key)
                );
                CREATE TABLE IF NOT EXISTS events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    experiment TEXT NOT NULL REFERENCES experiments(experiment),
                    run_key TEXT,
                    operation TEXT NOT NULL,
                    details TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                );
                PRAGMA user_version=1;
                COMMIT;
            """)
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT max_trials, max_tokens FROM experiments WHERE experiment=?", (experiment,)
            ).fetchone()
            if row:
                if (row["max_trials"], row["max_tokens"]) != (max_trials, max_tokens):
                    raise ValueError("Experiment limits are immutable")
            else:
                connection.execute(
                    "INSERT INTO experiments(experiment, max_trials, max_tokens) VALUES (?, ?, ?)",
                    (experiment, max_trials, max_tokens),
                )
                self._event(connection, experiment, None, "initialize", {
                    "max_trials": max_trials, "max_tokens": max_tokens,
                })
            connection.commit()
            return self.status(experiment)
        except BaseException:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _event(connection, experiment, run_key, operation, details):
        connection.execute(
            "INSERT INTO events(experiment, run_key, operation, details, timestamp) VALUES (?, ?, ?, ?, ?)",
            (experiment, run_key, operation, json.dumps(details, sort_keys=True), _now()),
        )

    @staticmethod
    def _experiment(connection, experiment):
        row = connection.execute(
            "SELECT * FROM experiments WHERE experiment=?", (experiment,)
        ).fetchone()
        if row is None:
            raise ValueError("Unknown experiment")
        return row

    @staticmethod
    def _run(connection, experiment, run_key):
        row = connection.execute(
            "SELECT * FROM runs WHERE experiment=? AND run_key=?", (experiment, run_key)
        ).fetchone()
        if row is None:
            raise ValueError("Unknown run key")
        return row

    @staticmethod
    def _totals(rows):
        active = ("reserved", "dispatched", "uncertain")
        terminal = ("settled", "overrun")
        return {
            "reserved_tokens": sum(row["reserved_tokens"] for row in rows if row["status"] in active),
            "reserved_trials": sum(row["trial_units"] for row in rows if row["status"] in active),
            "settled_tokens": sum(row["actual_tokens"] for row in rows if row["status"] in terminal),
            "settled_trials": sum(row["trial_units"] for row in rows if row["status"] in terminal),
        }

    def reserve(self, experiment, run_key, *, tokens, trial_units=1):
        experiment = _text(experiment, "experiment")
        run_key = _text(run_key, "run_key")
        tokens = _number(tokens, "tokens")
        if type(trial_units) is not int or trial_units not in (0, 1):
            raise ValueError("trial_units must be 0 or 1")
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            budget = self._experiment(connection, experiment)
            existing = connection.execute(
                "SELECT * FROM runs WHERE experiment=? AND run_key=?", (experiment, run_key)
            ).fetchone()
            if existing:
                if (existing["reserved_tokens"], existing["trial_units"]) != (tokens, trial_units):
                    raise ValueError("Run key already reserved with different parameters")
                connection.commit()
                return dict(existing)
            if budget["overrun"]:
                raise ValueError("Experiment is stopped after a provider overrun")
            rows = connection.execute("SELECT * FROM runs WHERE experiment=?", (experiment,)).fetchall()
            totals = self._totals(rows)
            if (totals["reserved_tokens"] + totals["settled_tokens"] + tokens > budget["max_tokens"] or
                    totals["reserved_trials"] + totals["settled_trials"] + trial_units > budget["max_trials"]):
                raise ValueError("Experiment budget exhausted")
            connection.execute(
                "INSERT INTO runs(experiment, run_key, reserved_tokens, trial_units, status, created_at) "
                "VALUES (?, ?, ?, ?, 'reserved', ?)",
                (experiment, run_key, tokens, trial_units, _now()),
            )
            self._event(connection, experiment, run_key, "reserve", {"tokens": tokens, "trial_units": trial_units})
            result = dict(self._run(connection, experiment, run_key))
            connection.commit()
            return result
        except BaseException:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

    def _transition(self, experiment, run_key, operation, *, reason=None, actual_tokens=None,
                    non_execution_evidence=None, receipt_sha256=None):
        experiment = _text(experiment, "experiment")
        run_key = _text(run_key, "run_key")
        if operation in ("uncertain", "cancel"):
            reason = _text(reason, "reason")
        if non_execution_evidence is not None:
            non_execution_evidence = _text(non_execution_evidence, "non_execution_evidence")
        if operation == "settle":
            actual_tokens = _number(actual_tokens, "actual_tokens")
            if receipt_sha256 is not None and (
                not isinstance(receipt_sha256, str) or len(receipt_sha256) != 64
                or any(c not in "0123456789abcdef" for c in receipt_sha256)
            ):
                raise ValueError("receipt_sha256 must be a lowercase SHA-256")
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            budget = self._experiment(connection, experiment)
            run = self._run(connection, experiment, run_key)
            state = run["status"]
            details = {}
            if operation == "dispatch":
                if state == "dispatched":
                    connection.commit()
                    return {**dict(run), "dispatch_granted": False}
                if state != "reserved":
                    raise ValueError("Only a reserved run can be dispatched")
                if budget["overrun"]:
                    raise ValueError("Experiment is stopped after a provider overrun")
                target = "dispatched"
            elif operation == "uncertain":
                if state == "uncertain":
                    connection.commit()
                    return dict(run)
                if state != "dispatched":
                    raise ValueError("Only a dispatched run can become uncertain")
                target = "uncertain"
                details = {"reason": reason}
            elif operation == "cancel":
                if state == "cancelled":
                    connection.commit()
                    return dict(run)
                if state in ("dispatched", "uncertain") and not non_execution_evidence:
                    raise ValueError("Dispatched or uncertain run requires non-execution evidence")
                if state not in ("reserved", "dispatched", "uncertain"):
                    raise ValueError("Run cannot be cancelled after settlement")
                target = "cancelled"
                details = {"reason": reason, "non_execution_evidence": non_execution_evidence}
            elif operation == "settle":
                if state in ("settled", "overrun"):
                    prior = connection.execute(
                        "SELECT details FROM events WHERE experiment=? AND run_key=? AND operation='settle'",
                        (experiment, run_key)).fetchone()
                    if (run["actual_tokens"] != actual_tokens or
                            json.loads(prior["details"]).get("receipt_sha256") != receipt_sha256):
                        raise ValueError("Settlement conflicts with recorded usage or receipt")
                    connection.commit()
                    return dict(run)
                if state not in ("dispatched", "uncertain"):
                    raise ValueError("Run must be dispatched before settlement")
                target = "overrun" if actual_tokens > run["reserved_tokens"] else "settled"
                details = {"actual_tokens": actual_tokens, "reserved_tokens": run["reserved_tokens"],
                           "receipt_sha256": receipt_sha256}
                if target == "overrun":
                    connection.execute("UPDATE experiments SET overrun=1 WHERE experiment=?", (experiment,))
            else:
                raise ValueError("Unknown operation")
            connection.execute(
                "UPDATE runs SET status=?, actual_tokens=? WHERE experiment=? AND run_key=?",
                (target, actual_tokens if operation == "settle" else None, experiment, run_key),
            )
            self._event(connection, experiment, run_key, operation, details)
            result = dict(self._run(connection, experiment, run_key))
            connection.commit()
            if operation == "dispatch":
                result["dispatch_granted"] = True
            return result
        except BaseException:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

    def dispatch(self, experiment, run_key):
        return self._transition(experiment, run_key, "dispatch")

    def uncertain(self, experiment, run_key, reason):
        return self._transition(experiment, run_key, "uncertain", reason=reason)

    def settle(self, experiment, run_key, *, actual_tokens, receipt_sha256=None):
        return self._transition(experiment, run_key, "settle", actual_tokens=actual_tokens,
                                receipt_sha256=receipt_sha256)

    def cancel(self, experiment, run_key, *, reason, non_execution_evidence=None):
        return self._transition(experiment, run_key, "cancel", reason=reason,
                                non_execution_evidence=non_execution_evidence)

    def status(self, experiment):
        experiment = _text(experiment, "experiment")
        connection = self._connect()
        try:
            connection.execute("BEGIN")
            budget = dict(self._experiment(connection, experiment))
            runs = [dict(row) for row in connection.execute(
                "SELECT * FROM runs WHERE experiment=? ORDER BY run_key", (experiment,)
            )]
            events = [dict(row) for row in connection.execute(
                "SELECT sequence, run_key, operation, details, timestamp FROM events "
                "WHERE experiment=? ORDER BY sequence", (experiment,)
            )]
            for event in events:
                event["details"] = json.loads(event["details"])
            budget.update(self._totals(runs), runs=runs, events=events, overrun=bool(budget["overrun"]))
            connection.commit()
            return budget
        finally:
            connection.close()
