# 0008: Codify owns reusable compilation and executable workflow artifacts

Status: accepted, 2026-10-30.

The user requested a reusable `codify` skill that extracts Skillify's compilation
work, accepts prompts/Markdown as authoring inputs, and produces cached executable
artifacts analogous to GitHub Agentic Workflows' generated lock files.

Codify owns native workflow templates, the optional locked Vercel AI SDK boundary,
and the compiler/runner. Skillify retains skill packaging and consumes that
engine through a generated standalone release. A deterministic sync check in
doctor prevents that distribution copy becoming another implementation.

A one-time semantic lowering step produces real native code. Compilation verifies
positive/rejection contracts and freezes code bytes, source/case hashes, native
entrypoint, and explicit inference declarations into a canonical JSON lock.
Normal execution uses its frozen code and fails on stale inputs. It never
implicitly rebuilds or invokes an agent to interpret source. No private workflow
DSL is added; native MAF/Rhai authoring and hosts remain Flowify's concern.

Lock artifacts and their authored inputs may be versioned. Temporary execution,
evidence, and cooperative publication locks remain ignored `.tkstack` state.
Verification uses isolated bounded workers; publication is atomic with drift
checks. Standalone copied packages remain usable without the original checkout.

This model avoids repeated interpretation of codifiable procedures. It does not
provide automatic semantic equivalence for arbitrary prose, signatures, sandbox
isolation, hermetic dependency closure, or guaranteed absence of model calls.
Residual inference remains explicit, configured through the existing native AI
SDK profiles, and subject to deterministic output/effect gates.
