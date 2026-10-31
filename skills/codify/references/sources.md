# Primary sources and differences

[GitHub Agentic Workflows](https://github.com/github/gh-aw) describes Markdown
with configuration frontmatter, compiled by `gh aw compile` to `.lock.yml` for
GitHub Actions execution. See its
[README](https://github.com/github/gh-aw/blob/main/README.md#how-agentic-workflows-work)
and [workflow editing rules](https://github.com/github/gh-aw/blob/main/.github/aw/workflow-editing.md).
Read on 2026-10-30. This is conceptual inspiration; no upstream code is copied.

GH-AW compilation lowers Actions configuration; its Markdown agent body can
still be interpreted by an AI engine at runtime. A generated lock alone does
not remove that inference. Codify instead freezes the **implemented native
procedure** after one-time semantic lowering and contract verification. Its
runner executes those bytes and does not reinterpret the source Markdown.
Residual inference, if needed by that code, stays explicit and probabilistic.
Codify is not a GH-AW compiler, replacement, or compatible `.lock.yml` producer.

The native workflow templates and version-pinned Vercel AI SDK boundary were
extracted from the owned Skillify package. The inference reference records
actual SDK versions, official APIs, concurrency controls, and verification
limits. Use the real MAF/Grok hosts for those workflow languages; this artifact
format only freezes code/resources and an interpreter invocation.
