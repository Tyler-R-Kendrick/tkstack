# Templates and native generators

Reuse the project's actual engine and format. Examples include T4 for text/
source generation, Copier/Jinja for parameterized projects, `.NET new` template
packages for .NET scaffolding, and language-native generators. Do not invent a
prompt-only pseudo-generator or a private placeholder language when these fit.

Model explicit typed parameters and validate them before publishing output.
Use language-aware literal/identifier escaping. Raw substitutions in code can
introduce syntax errors or executable input. Never interpolate a path parameter
without containment/identifier validation. Pin engine/template/input versions.
Remove incidental clocks, randomness, network state, absolute paths, and unstable
enumeration from output unless they are explicit required inputs.

## T4

T4 mixes text with host-executed control blocks. `<# ... #>` runs generation
logic, `<#= ... #>` emits values, and directives select the template/output,
parameters, references, and includes. Reuse `.ttinclude` helpers where suitable.
Design-time templates generate files; preprocessed runtime templates produce a
class whose `TransformText()` can be called by an application. These hosts and
build lifecycles are different; declare the actual required engine.

The packaged [limits template](../examples/t4/limits.tt) illustrates a typed
integer input, bounds validation, invariant formatting, and fixed owned C# output.
Bind `WorkerLimit` through the real compatible host. It is source guidance, not
a tested portable TextTransform command; do not assume Visual Studio, an SDK,
or a particular T4 CLI exists in every harness. Hosts can execute template code,
so inspect templates/includes/dependencies before executing trusted inputs.

## Copier example

The packaged [Copier template](../examples/copier/copier.yml) uses native YAML
questions and Jinja. It validates a label and a bounded worker count and emits
one Python configuration module. It defines no hooks/tasks and requires no
model inference. Use a compatible pinned Copier CLI and an absent owned output:

```sh
copier copy --defaults --data display_name=Example --data worker_limit=4 \
  <reusify-directory>/examples/copier <new-output-directory>
```

The example uses Copier **9.7.1**, with a bundled hashed transitive
[dependency lock](../examples/copier/requirements.lock) resolved and tested on
CPython 3.12/Linux. Regenerate and validate it for another interpreter/platform.
Run its native verification command:

```sh
python3 <reusify-directory>/examples/copier/verify.py --copier <actual-copier-executable>
```

It checks quotes, non-BMP Unicode, code-shaped literal input, invalid parameters,
generated Python compilation/consumption, and unchanged rerendered source bytes.
Missing native runtime returns exit 3, not success. It does not run T4/Roslyn.
The template decodes escaped JSON deliberately: a JSON string literal alone is
not a correct Python literal for all Unicode. Reuse the tested representation.
Copier's answers file
records native provenance and may contain a local template path; do not publish
machine-specific state or credentials as a portable template version.

## Generated-file ownership

Declare which outputs are regenerated and which files remain authored. Never
overwrite manual edits or another worker's outputs silently. Use a preview/diff,
native update/merge mechanism, or separate generated directory with an explicit
contract. Snippets and ordinary scaffolds do not acquire automatic updates.

Concurrent renders need private output roots, stable input-to-output names,
bounded workers, and safe shared caches. Reject collisions and path traversal.
For build-time generators, declare inputs/outputs so the actual build graph can
invalidate correctly. Check unchanged reruns, changed inputs, invalid inputs,
and fresh-versus-incremental output. A successful render is not compilation or
behavior proof, and a cache hit is not proof of incrementality.
