# Python CLI contract generator

Use a version 1 JSON object with exactly `entrypoint` (project-relative `.py`),
`risk` and `distinction` (specific descriptions of at least 20 characters),
`timeout` (1–60 seconds), and `cases` (1–32). Every case has a distinct `name`,
string `args`, an integer `exit`, and at least one independent `stdout_text`,
`stdout_json` or nonempty `stderr_contains` observation. `stdout_text` and
`stdout_json` are mutually exclusive. JSON null is a valid expected value.
`{root}` and `{tmp}` in arguments resolve to the checkout and an isolated
per-case temporary directory. The CLI is invoked via `sys.executable` with
`shell=False`, and each case runs with its temporary directory as cwd.

```sh
python3 <testify>/scripts/testify.py plan --project /project --target tests/test_cli.py --spec /tmp/cases.json
python3 <testify>/scripts/testify.py create --project /project --target tests/test_cli.py --spec /tmp/cases.json
python3 <testify>/scripts/testify.py run --project /project --target tests/test_cli.py
```

The direct `plan` helper returns generated source for review and writes nothing. The compiled typed runner may initialize its ignored workspace scratch as documented in its execution contract. `create`
requires an existing parent and atomically refuses an existing target, symlink
or out-of-project path. It does not run the test. `run` executes that file as
Python, reports native output and a bounded exit; it is not a sandbox. Paths,
input, code, and expected outputs must come from the actual project/task. A
single unittest with subtests preserves related cases without one file per case.
Use an existing suite directly if it already owns the relevant contract.
