# Python CLI contract generator

Use a version 1 JSON object with exactly `entrypoint` (project-relative `.py`),
`risk` and `distinction` (specific descriptions of at least 20 characters),
`cases` (1–32), and an optional `timeout` (1–60 seconds, default 30). Every case has a distinct `name`,
string `args`, an integer `exit`, and at least one independent `stdout_text`,
`stdout_json` or nonempty `stderr_contains` observation. `stdout_text` and
`stdout_json` are mutually exclusive. JSON null is a valid expected value.
`{root}` and `{tmp}` in arguments resolve to the checkout and an isolated
per-case temporary directory. The CLI is invoked via `sys.executable` with
`shell=False`, and each case runs with its temporary directory as cwd. Direct
POSIX runs place a case in its own process group and stop ordinary descendants
on completion or timeout, before reaping its group leader. Direct POSIX runs
require non-reaping `waitid` support and the default `SIGCHLD` disposition;
they fail closed if the host cannot provide it. Under the compiled runner, the case shares the outer
group, which is cleaned up when that invocation finishes. Detached descendants,
non-POSIX children, and remote effects can outlive cancellation and require
separate supervision and reconciliation. Captured output is read with a 1 MiB
per-stream limit after the process stops; temporary files may grow during the run.

```sh
python3 <testify>/scripts/testify.py plan --project /project --target tests/test_cli.py --spec /tmp/cases.json
python3 <testify>/scripts/testify.py create --project /project --target tests/test_cli.py --spec /tmp/cases.json
python3 <testify>/scripts/testify.py run --project /project --target tests/test_cli.py
```

The direct `plan` helper returns generated source for review and writes nothing. The compiled typed runner may initialize its ignored workspace scratch as documented in its execution contract. `create`
requires an existing parent and atomically refuses an existing target, symlink
or out-of-project path. It does not run the test. `run` executes that file as
Python, reports native output, elapsed time and a bounded exit; it is not a sandbox.
Direct `run` has a 120-second overall deadline across cases and owns the
generated test's process group. Compiled invocations also have their own host
and native deadlines, which may expire earlier. A direct overall timeout reports
`status: timeout` and exit 124; a direct SIGINT or SIGTERM reports
`status: interrupted`, its signal, and elapsed time after group cleanup. Paths,
input, code, and expected outputs must come from the actual project/task. A
single unittest with subtests preserves related cases without one file per case.
Use an existing suite directly if it already owns the relevant contract.
