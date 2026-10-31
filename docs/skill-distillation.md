# Portable skill distillation

The **154 repository skills** present at the start were indexed by purpose,
triggers, branch structure, source, and ownership. Selected procedure/reference
details informed independently written portable adaptations. This review ranks
static suitability: likely reuse, concrete procedural value, portability, fit
with tkstack standards, and an existing owner. It is not usage telemetry, a
word-for-word review of every resource, or a measured model-performance ranking.
System/cloud plugin catalogs and private session histories are outside scope.

The [complete decision inventory](skill-distillation.json) accounts for every
original skill, its entrypoint hash, canonical source, pinned revision/license,
disposition, and destination. Of those, 128 upstream skills contribute general
methods, 13 remain specialist integrations without another portable copy, and
13 existing owned packages receive the overlapping material.

## Selected owners

| Priority | Outcome | Portable owner | Main source learnings |
| --- | --- | --- | --- |
| Core | Ground a system, rationale, or failure | [`investigate`](../skills/investigate/SKILL.md), new | Pstack how/why, Matt diagnosis/research, trustworthy trace/search evidence |
| Core | Plan, design, build, verify, review, deliver | [`sdlc`](../skills/sdlc/SKILL.md), expanded | Matt specs/slices/interfaces, Pstack design/evidence, Tstack PR lifecycle, Lever coordination, Ponytail skepticism |
| Core | Make consistent engineering decisions | [`tkstack-principles`](../skills/tkstack-principles/SKILL.md), expanded | Complete minimal changes, useful interfaces, structural enforcement, artifact evidence |
| Core | Learn and enforce durable lessons | `learn`, `skillify`, `hookify`, `instructify`, `flowify` | Lever steer-once, Pstack reflection, Matt agent writing and enforcement boundaries |
| Core | Improve a measured outcome | `hill-climb`, expanded | Lever loop cards/arms, sensitivity, noise, real execution, bounded hypotheses |
| Core | Review output quality | `unslop`, expanded | Purpose, concrete defects, meaningful tests, actual visual/media inspection |
| By task | Design interfaces and systems | `open-design`, expanded | Impeccable surface intent, Stitch semantic systems, Higgsfield brand fidelity |
| By task | Produce media | `fal-ai`, expanded | Higgsfield production briefs, identity/reference constraints, job identity and output inspection |
| By task | Develop human-facing writing | [`write`](../skills/write/SKILL.md), new | Matt fragments, shaping, concept grounding, voice and author edits |
| By task | Maintain repository knowledge/handoffs | [`document`](../skills/document/SKILL.md), new | OpenWiki lifecycle boundaries, source evidence, glossary/ADRs, resumable handoffs |
| Explicit tool | Compress context without losing evidence | `rtk`, `headroom`, repackaged | Runtime boundaries, recoverable originals, measured claims and preserved routing |

Synthesis is placed inside existing skills where the outcome overlaps. Review
and planning are scoped SDLC modes; they do not invoke its full swarm/PR workflow.
Writing is distinct from anti-slop grading, and documentation is distinct from
agent policy. These distinctions justify the three new packages.

## Disclosure and portability

The **16 owned packages produced by this review** have concise entrypoints, conditional pointers to
`references/*.md`, bundled licenses, and marketplace entries. The eight existing
long procedures remain as referenced operating guides; their helper code,
templates, record formats, and behavioral gates are preserved. A full workflow
loads its operating guide before acting, while a scoped branch reads its matching
reference. Source attribution is included inside each standalone package.

General methods use actual capabilities instead of hardcoded models or one
harness's delegation API. Provider runtime calls stay in adapters. Missing tools
do not acquire a simulated success fallback. OpenWiki's deterministic lifecycle,
Headroom, RTK, fal, and OpenDesign still require their real runtimes/connections
for those effects. Existing native packages remain available and unchanged.

Deliberate exclusions include forced interviews and paragraph approvals, private
history mining, blanket external-message permissions, automatic publication or
merge grants, fixed model rosters, mandatory E2E suites, universal benchmark
thresholds, and interpreting an execution denial as an interpreter workaround.
The user's BDD/contracts, evidence, concurrency, and authority requirements win.

## Validation and its limits

Validation checks each complete standalone package's metadata, local references,
licenses, and Python syntax, including copies outside the dotfiles tree. Existing
behavioral tests exercise the unchanged helpers. Vendor hash/mode/inventory,
installation repeatability, and native configuration are checked separately.
The review also compares representative selection/transfer/boundary cases below.
These are editorial contract checks, not fresh-agent trigger or task-performance
experiments; no optimizer scores or model-quality improvement are claimed.

| Case | Expected scope |
| --- | --- |
| Explain retry ownership in this repository | Investigate system tracing; cite real callers/state |
| Diagnose a captured launch error in another harness | Investigate diagnosis; distinguish no execution from bad agent behavior |
| Draft an article from supplied notes | Write a complete draft; preserve source notes |
| Write the supplied JSON to a file | Ordinary file operation; no narrative writing workflow |
| Refresh repository architecture docs | Document current source; use OpenWiki only if its real lifecycle is selected/available |
| Change scoped agent instructions | Instructify; preserve imports and owners |
| Review a diff only | SDLC review reference; no automatic worktrees, agents, PRs, or merge |
| Full SDLC implementation | Preserve workload/DAG/COW/BDD/contracts/evidence/stacked-delivery procedure |
| Generic design review without OpenDesign | Portable design procedure; no claim the provider ran |
| Generate with explicit Higgsfield | Preserve that provider; fal guidance cannot substitute fal execution |
| Improve a skill using a source idea | Update its owner; structural validation is not measured optimization |

The before-state packages and transformation/validation receipts are retained
locally under `.tkstack/evidence/distillation/`. The decision inventory and
package-contained provenance are the shareable source record.
