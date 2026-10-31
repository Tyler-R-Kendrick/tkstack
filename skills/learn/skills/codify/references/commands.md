# Invoke Codify as a tool

From an authored workflow directory, with `CODIFY` replaced by the actual helper
path (not an environment requirement):

```sh
python3 /path/to/codify/scripts/codify.py scaffold /repo/procedure.md --target /repo/normalize
# Implement /repo/normalize/scripts/workflow.py; author cases.json and tool guide.
cd /repo/normalize
python3 /path/to/codify/scripts/codify.py compile PROMPT.md \
  --entrypoint scripts/run.py --cases cases.json --output scripts/workflow.lock.json
python3 /path/to/codify/scripts/codify.py check scripts/workflow.lock.json
python3 /path/to/codify/scripts/codify.py run scripts/workflow.lock.json --input input.json
```

For the complete bundled example, set source/root/entrypoint/cases/output to
`examples/normalize-labels/` or run `run` on its existing
`scripts/workflow.lock.json` with `--input -` and a JSON object on stdin:
`{"labels":[" b ","a","a"]}` produces `{"labels":["a","b"]}`.

| Command / parameter | Contract |
| --- | --- |
| `scaffold source --target absent-dir` | Copy exact authoring input to `PROMPT.md`, MIT license, native workflow/CLI starters and tool guide; status `workflow-draft`. Never overwrite a directory. |
| `scaffold --backend python\|ai-sdk` | Python default; optional AI SDK backend copies TypeScript CLI/tool export, runtime, empty profiles, and actual npm dependency lock. |
| `compile source --entrypoint file --cases file` | Verify and freeze an implemented workflow. Source may be any UTF-8 prompt/Markdown/provenance file. Entrypoint must accept `--input <json-file>` and print one JSON value on success. |
| `--root directory` | Build containment root; default source parent. All source, cases, includes, entrypoint, and output belong within it. |
| `--output file` | Default source basename with `.lock.json`; for skills use `scripts/workflow.lock.json`. Parent must already exist. |
| `--include path` (repeatable) | Additional code/resources to freeze, within root. The entrypoint's entire directory is included by default. Paths are relative to the invocation directory. Symlinked build inputs are rejected. |
| `--profile name` (repeatable) | Declare residual inference profiles; absent means `none`. Profile names are frozen; this is an audited declaration, not network isolation or a static proof. |
| `--jobs 1..16` | Contract workers; default 4. Stable input order, private runtime directories, all workers joined. |
| `compile --dry-run` | Pure file/hash plan; no workflow execution, publication, state, or verification claim. |
| `check artifact` | Read-only schema/hash/provenance/current-input check. Does not execute code, fetch dependencies, create state, or assert fresh semantic correctness. |
| `run artifact --input file\|-` | Check freshness, materialize the locked code image in private state, run native CLI. No compilation, prompt interpretation, or provider selection. |
| `--project directory` | For compile/run only: active project owning `.tkstack` state. Compile defaults to the build project; run defaults to current project. |
| `--timeout 1..300` | Compile/run native process deadline in seconds; default 30 per invocation. POSIX process group terminated at deadline/interruption. |
| `--dependencies node_modules` | Explicit preinstalled Node dependencies; direct versions checked against the frozen package manifest. No dependency download at compile/run time. Use `npm ci` against the frozen package lock first. |
| `--config profiles.json` | Compile/run explicit inference configuration. Keys must be among declared profile names; rejected for a no-inference lock. Secrets remain environment-variable references. |

All paths may contain spaces. Do not shell-interpolate user text into a command;
use argument arrays. Input is a JSON object within 1 MiB; duplicate fields and
non-finite numbers are rejected. Successful output is one JSON value within
1 MiB. Diagnostics go to stderr. Runtime code retains its normal authorized
environment; copied working directory is temporary under `.tkstack/sessions/<session>/`. Workflows must take external
repository/output paths explicitly rather than guessing the temporary cwd.

## Contract cases

```json
{"version":1,"cases":[
  {"id":"sort","input":{"labels":["b","a","a"]},"exit":0,"output":{"labels":["a","b"]}},
  {"id":"reject","input":{"labels":[1]},"exit":1}
]}
```

Use 2–64 uniquely named cases, including success and rejection. Each input is an
object; each exit is an integer 0–125. Only success cases have `output`. Rejection
must not emit success stdout. Expected JSON types/values compare canonically;
no-inference successes run twice. These examples complement domain review.

Scaffold/compile/check success exits 0; invalid inputs, stale artifacts, failed
cases, collisions, or runtime setup failure exit 1; usage exits 2. `run` forwards
the workflow's normal exit; unfinished starter exits 3. A runtime signal maps
to failure 1. Never treat a draft or missing dependency as successful execution.
