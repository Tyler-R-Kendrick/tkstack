# Make the pointer choose the right procedure

Treat the main `SKILL.md` as the package's table of contents/index page, not
the full manual. Include purpose, distinct selection triggers, essential scope
and safety boundaries, and a condition-to-reference map. Move detailed steps,
features, subcommands, parameters, variants, examples, and provenance into
`references/*.md`. The skill is an intermediary code-mode prompt. Put the
actual workflow definition/algorithm in `scripts/` and index how to invoke it
as a tool; Markdown is not the production executable.

Map the skill's actual public surface before authoring prose. Each main topic
or feature needs a direct index pointer. If the skill has subcommands, list
each command and its purpose, including the default when the command is
omitted. Link each command to its full behavior, inputs/parameters, defaults,
errors, output, and completion condition. Parameter names may appear in a
short index summary; keep their full contracts/examples in the linked page.
Do not invent commands or switches merely to fill an outline.

Each public subcommand lives in `commands/<name>.md` with YAML frontmatter for
its OpenAI function-tool signature and separate CLI/artifact bindings. See
[subcommand authoring](subcommands.md). Index the file directly; its body owns
usage and parameter explanations, while executable dispatch uses the schema.
Include read-only help by default and preserve nested paths, aliases, flags,
typed inputs, and the no-command behavior across CLI and agent invocation.

For a small skill, one operating reference may cover several topics using
precise section links. Split distinct branches when that reduces the context
needed for a task. Keep shared invariants in one linked reference and make
branch prerequisites explicit. Index links must describe their destination's
actual content; no empty pages or generic "more details" placeholders in a
completed package. The scaffolder creates an index, tool interface and three
draft topic pages, plus an executable workflow starter. Replace/split the docs
and implement the actual script to fit the real procedure.

Every reference pointer states when to load it. A bare "see references" makes
the agent guess; a condition such as "When updating a stale PR, read delivery"
selects a real branch. Keep essential guardrails at the entrypoint so a reader
does not have to discover whether the task is read-only or requires a runtime.

Prefer one direct hop from the entrypoint to each operational reference. A
reference may link to an exact schema or specialized source when needed, but
do not create a chain of indexes the reader must traverse to find the action.
Do not load every reference merely because the skill was selected. Read only
the selected branch and its necessary prerequisites. Avoid copying full
subcommand procedures or parameter manuals into the index as well as references.

When adapting a catalog, inventory all candidates, then rank static suitability
by likely task reuse, concrete procedural value, portability, fit with current
preferences, and duplication. Label that judgment accurately; token counts,
source popularity, and an installed package are not performance evidence.

Merge an overlapping procedure into its existing owned package. Create a new
skill only when it has a distinct trigger, output, and completion condition.
Leave provider-specific APIs and account setup in a named adapter. Declare the
fallback and its lost guarantees; do not pretend unavailable tools executed.

Portable packages contain their own Markdown, licenses, schemas, templates, and
helper files. Cite exact upstream revision/path URLs for attribution, but do not
require a sibling vendor checkout to read the procedure. Preserve source license
obligations for copied material. Independently written synthesis must not claim
to be an exact port or a measured improvement.

Check a reproducing use, a distinct transfer use, and a negative selection case.
For example, "draft an article" selects writing, while "write this JSON file"
does not. Validate the actual package copy and its local references outside the
dotfiles tree. Structural validity establishes packaging, not trigger accuracy.
