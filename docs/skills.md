# Installed skill inventory

All 19 repository packages share reserved help/version, explicit contract models,
retained-report verification, native helper bindings where applicable, and
reviewed compiled artifacts. [Normalization coverage](normalization.md) describes
what runs mechanically and what still requires actual semantic/provider work.


Skills install by origin. The 15 skills under development in `skills/` join
Codex, Claude Code, and Cursor. Harness-independent outside skills, including the
four third-party-derived packages in `.agents/skills/`, install only to the shared
`.agents/skills/` directory. Pstack and its Cursor Team Kit dependency install
only to `.cursor/skills/`. Graphify and Impeccable ship a distinct build for each
harness, so each harness keeps its native copy. `harnesses/skills.json` records
this placement. Links point to source instructions.
Use `/name` in slash-command harnesses or `$name` in Codex. User-only entries
preserve upstream `disable-model-invocation: true` policy.

The personal `learn` skill maintains the shared steering store and supports
explicit report/audit and procedural skill-improvement modes. See
[learning](learning.md), [integration readiness](integrations.md), and the
[initial compatibility review](evaluation.md). Matt's TDD skill is `matt-tdd`;
its internal calls are adapted while the pinned source stays unchanged.

## Skills under development (15)

| Skill | Bucket | Invocation |
| --- | --- | --- |
| [`codify`](../skills/codify/SKILL.md) | personal | User or model |
| [`document`](../skills/document/SKILL.md) | personal | User or model |
| [`flowify`](../skills/flowify/SKILL.md) | personal | User or model |
| [`hill-climb`](../skills/hill-climb/SKILL.md) | personal | User only |
| [`hookify`](../skills/hookify/SKILL.md) | personal | User or model |
| [`instructify`](../skills/instructify/SKILL.md) | personal | User or model |
| [`investigate`](../skills/investigate/SKILL.md) | personal | User or model |
| [`learn`](../skills/learn/SKILL.md) | personal | User or model |
| [`lintify`](../skills/lintify/SKILL.md) | personal | User or model |
| [`reusify`](../skills/reusify/SKILL.md) | personal | User or model |
| [`sdlc`](../skills/sdlc/SKILL.md) | personal | User only |
| [`skillify`](../skills/skillify/SKILL.md) | personal | User or model |
| [`tkstack-principles`](../skills/tkstack-principles/SKILL.md) | personal | User or model; native startup pointer |
| [`unslop`](../skills/unslop/SKILL.md) | personal | User or model |
| [`write`](../skills/write/SKILL.md) | personal | User or model |

## Third-party-derived packages (4)

These wrap or distill outside tools and live in `.agents/skills/`, not in the
root `skills/` directory reserved for skills under active development. They keep
the shared typed contract and marketplace entries.

| Skill | Bucket | Invocation |
| --- | --- | --- |
| [`fal-ai`](../.agents/skills/fal-ai/SKILL.md) | third-party-derived | User or model |
| [`headroom`](../.agents/skills/headroom/SKILL.md) | third-party-derived | User or model |
| [`open-design`](../.agents/skills/open-design/SKILL.md) | third-party-derived | User or model |
| [`rtk`](../.agents/skills/rtk/SKILL.md) | third-party-derived | User or model |

The [curation review](skill-distillation.md) explains the portable owners, source
choices, conditional references, and retained native specialists.

## Graphify (1)

The official Graphify Labs skill uses matching native Codex/Claude variants and
its generic Agent Skills variant for Cursor. All eight reference sidecars are
bundled in each generated view. The pinned local runtime, MCP connection, hooks,
state conventions, and native validation are described in [Graphify setup](graphify.md).

## Official Caveman (22)

The official 4.0.1 snapshot includes all root skills below and the three
Cavecrew agents. Native hook behavior, startup controls, and host limits are
documented in [Caveman setup](caveman.md).

| Skill | Source |
| --- | --- |
| `cavecrew` | [Official skill](../vendor/caveman/skills/cavecrew/SKILL.md) |
| `caveman` | [Official skill](../vendor/caveman/skills/caveman/SKILL.md) |
| `caveman-commit` | [Official skill](../vendor/caveman/skills/caveman-commit/SKILL.md) |
| `caveman-compress` | [Official skill](../vendor/caveman/skills/caveman-compress/SKILL.md) |
| `caveman-discover` | [Official skill](../vendor/caveman/skills/caveman-discover/SKILL.md) |
| `caveman-evidence-review` | [Official skill](../vendor/caveman/skills/caveman-evidence-review/SKILL.md) |
| `caveman-explore` | [Official skill](../vendor/caveman/skills/caveman-explore/SKILL.md) |
| `caveman-help` | [Official skill](../vendor/caveman/skills/caveman-help/SKILL.md) |
| `caveman-learn` | [Official skill](../vendor/caveman/skills/caveman-learn/SKILL.md) |
| `caveman-manage` | [Official skill](../vendor/caveman/skills/caveman-manage/SKILL.md) |
| `caveman-optimize` | [Official skill](../vendor/caveman/skills/caveman-optimize/SKILL.md) |
| `caveman-review` | [Official skill](../vendor/caveman/skills/caveman-review/SKILL.md) |
| `caveman-setup` | [Official skill](../vendor/caveman/skills/caveman-setup/SKILL.md) |
| `caveman-stats` | [Official skill](../vendor/caveman/skills/caveman-stats/SKILL.md) |
| `investigate-first` | [Official skill](../vendor/caveman/skills/investigate-first/SKILL.md) |
| `lean-build` | [Official skill](../vendor/caveman/skills/lean-build/SKILL.md) |
| `megacave` | [Official skill](../vendor/caveman/skills/megacave/SKILL.md) |
| `migration` | [Official skill](../vendor/caveman/skills/migration/SKILL.md) |
| `safe-refactor` | [Official skill](../vendor/caveman/skills/safe-refactor/SKILL.md) |
| `surgical-patch` | [Official skill](../vendor/caveman/skills/surgical-patch/SKILL.md) |
| `ultracave` | [Official skill](../vendor/caveman/skills/ultracave/SKILL.md) |
| `verify-and-stop` | [Official skill](../vendor/caveman/skills/verify-and-stop/SKILL.md) |

## OpenWiki (1)

[`openwiki`](../vendor/openwiki/integrations/openwiki/SKILL.md) is LangChain's
official skill for repository wiki retrieval, generation, and updates through
its resumable MCP lifecycle. The local runtime and all three MCP host identities
are configured; see [installation and evidence](openwiki.md).

## GitHub Lever (16)

Lever's native menu exposes `/lever`; the other skills are routed verbs with
upstream `user-invocable: false` metadata preserved. Menus and Copilot-specific
capabilities depend on the actual host. See [setup and dials](lever.md).

| Verb | Skill |
| --- | --- |
| Entry, setup, spend, help | [`lever`](../vendor/lever/skills/lever/SKILL.md) |
| automate | [`automate-it`](../vendor/lever/skills/automate-it/SKILL.md) |
| deliver | [`autonomous-delivery`](../vendor/lever/skills/autonomous-delivery/SKILL.md) |
| autonomy | [`autonomy-dial`](../vendor/lever/skills/autonomy-dial/SKILL.md) |
| brief | [`brief`](../vendor/lever/skills/brief/SKILL.md) |
| review | [`cross-model-review`](../vendor/lever/skills/cross-model-review/SKILL.md) |
| arms | [`experiment-arms`](../vendor/lever/skills/experiment-arms/SKILL.md) |
| loop | [`find-the-loop`](../vendor/lever/skills/find-the-loop/SKILL.md) |
| backlog | [`keep-the-pool-full`](../vendor/lever/skills/keep-the-pool-full/SKILL.md) |
| land | [`landing-plan`](../vendor/lever/skills/landing-plan/SKILL.md) |
| shepherd | [`pr-shepherd`](../vendor/lever/skills/pr-shepherd/SKILL.md) |
| status | [`progress-contract`](../vendor/lever/skills/progress-contract/SKILL.md) |
| mirror | [`prompt-mirror`](../vendor/lever/skills/prompt-mirror/SKILL.md) |
| refactor | [`refactor-pipeline`](../vendor/lever/skills/refactor-pipeline/SKILL.md) |
| health | [`run-health-review`](../vendor/lever/skills/run-health-review/SKILL.md) |
| steer | [`steer-once`](../vendor/lever/skills/steer-once/SKILL.md) |

## Pstack (34)

| Skill | Bucket | Invocation |
| --- | --- | --- |
| [`architect`](../vendor/pstack/skills/architect/SKILL.md) | main | User only |
| [`arena`](../vendor/pstack/skills/arena/SKILL.md) | main | User only |
| [`automate-me`](../vendor/pstack/skills/automate-me/SKILL.md) | main | User only |
| [`figure-it-out`](../vendor/pstack/skills/figure-it-out/SKILL.md) | main | User only |
| [`how`](../vendor/pstack/skills/how/SKILL.md) | main | User or model |
| [`interrogate`](../vendor/pstack/skills/interrogate/SKILL.md) | main | User only |
| [`poteto-mode`](../vendor/pstack/skills/poteto-mode/SKILL.md) | main | User only |
| [`principle-boundary-discipline`](../vendor/pstack/skills/principle-boundary-discipline/SKILL.md) | main | User only |
| [`principle-build-the-lever`](../vendor/pstack/skills/principle-build-the-lever/SKILL.md) | main | User only |
| [`principle-encode-lessons-in-structure`](../vendor/pstack/skills/principle-encode-lessons-in-structure/SKILL.md) | main | User only |
| [`principle-exhaust-the-design-space`](../vendor/pstack/skills/principle-exhaust-the-design-space/SKILL.md) | main | User only |
| [`principle-experience-first`](../vendor/pstack/skills/principle-experience-first/SKILL.md) | main | User only |
| [`principle-fix-root-causes`](../vendor/pstack/skills/principle-fix-root-causes/SKILL.md) | main | User only |
| [`principle-foundational-thinking`](../vendor/pstack/skills/principle-foundational-thinking/SKILL.md) | main | User only |
| [`principle-guard-the-context-window`](../vendor/pstack/skills/principle-guard-the-context-window/SKILL.md) | main | User only |
| [`principle-laziness-protocol`](../vendor/pstack/skills/principle-laziness-protocol/SKILL.md) | main | User only |
| [`principle-make-operations-idempotent`](../vendor/pstack/skills/principle-make-operations-idempotent/SKILL.md) | main | User only |
| [`principle-migrate-callers-then-delete-legacy-apis`](../vendor/pstack/skills/principle-migrate-callers-then-delete-legacy-apis/SKILL.md) | main | User only |
| [`principle-minimize-reader-load`](../vendor/pstack/skills/principle-minimize-reader-load/SKILL.md) | main | User only |
| [`principle-never-block-on-the-human`](../vendor/pstack/skills/principle-never-block-on-the-human/SKILL.md) | main | User only |
| [`principle-outcome-oriented-execution`](../vendor/pstack/skills/principle-outcome-oriented-execution/SKILL.md) | main | User only |
| [`principle-prove-it-works`](../vendor/pstack/skills/principle-prove-it-works/SKILL.md) | main | User only |
| [`principle-redesign-from-first-principles`](../vendor/pstack/skills/principle-redesign-from-first-principles/SKILL.md) | main | User only |
| [`principle-separate-before-serializing-shared-state`](../vendor/pstack/skills/principle-separate-before-serializing-shared-state/SKILL.md) | main | User only |
| [`principle-sequence-verifiable-units`](../vendor/pstack/skills/principle-sequence-verifiable-units/SKILL.md) | main | User only |
| [`principle-subtract-before-you-add`](../vendor/pstack/skills/principle-subtract-before-you-add/SKILL.md) | main | User only |
| [`principle-type-system-discipline`](../vendor/pstack/skills/principle-type-system-discipline/SKILL.md) | main | User only |
| [`reflect`](../vendor/pstack/skills/reflect/SKILL.md) | main | User only |
| [`setup-pstack`](../vendor/pstack/skills/setup-pstack/SKILL.md) | main | User or model |
| [`show-me-your-work`](../vendor/pstack/skills/show-me-your-work/SKILL.md) | main | User only |
| [`tdd`](../vendor/pstack/skills/tdd/SKILL.md) | main | User only |
| [`typescript-best-practices`](../vendor/pstack/skills/typescript-best-practices/SKILL.md) | main | User or model |
| [`pstack-unslop`](../vendor/pstack/skills/unslop/SKILL.md) | main | User or model |
| [`why`](../vendor/pstack/skills/why/SKILL.md) | main | User or model |

## Cursor Team Kit (18)

| Skill | Bucket | Invocation |
| --- | --- | --- |
| [`check-compiler-errors`](../vendor/cursor-team-kit/skills/check-compiler-errors/SKILL.md) | main | User or model |
| [`control-cli`](../vendor/cursor-team-kit/skills/control-cli/SKILL.md) | main | User or model |
| [`control-ui`](../vendor/cursor-team-kit/skills/control-ui/SKILL.md) | main | User or model |
| [`deslop`](../vendor/cursor-team-kit/skills/deslop/SKILL.md) | main | User or model |
| [`fix-ci`](../vendor/cursor-team-kit/skills/fix-ci/SKILL.md) | main | User or model |
| [`fix-merge-conflicts`](../vendor/cursor-team-kit/skills/fix-merge-conflicts/SKILL.md) | main | User or model |
| [`get-pr-comments`](../vendor/cursor-team-kit/skills/get-pr-comments/SKILL.md) | main | User or model |
| [`loop-on-ci`](../vendor/cursor-team-kit/skills/loop-on-ci/SKILL.md) | main | User or model |
| [`make-pr-easy-to-review`](../vendor/cursor-team-kit/skills/make-pr-easy-to-review/SKILL.md) | main | User or model |
| [`new-branch-and-pr`](../vendor/cursor-team-kit/skills/new-branch-and-pr/SKILL.md) | main | User or model |
| [`pr-review-canvas`](../vendor/cursor-team-kit/skills/pr-review-canvas/SKILL.md) | main | User only |
| [`review-and-ship`](../vendor/cursor-team-kit/skills/review-and-ship/SKILL.md) | main | User or model |
| [`run-smoke-tests`](../vendor/cursor-team-kit/skills/run-smoke-tests/SKILL.md) | main | User or model |
| [`thermo-nuclear-code-quality-review`](../vendor/cursor-team-kit/skills/thermo-nuclear-code-quality-review/SKILL.md) | main | User only |
| [`verify-this`](../vendor/cursor-team-kit/skills/verify-this/SKILL.md) | main | User or model |
| [`weekly-review`](../vendor/cursor-team-kit/skills/weekly-review/SKILL.md) | main | User or model |
| [`what-did-i-get-done`](../vendor/cursor-team-kit/skills/what-did-i-get-done/SKILL.md) | main | User or model |
| [`workflow-from-chats`](../vendor/cursor-team-kit/skills/workflow-from-chats/SKILL.md) | main | User or model |

## Theo's Tstack (9)

| Skill | Bucket | Invocation |
| --- | --- | --- |
| [`babysit-pr`](../vendor/tstack/skills/babysit-pr/SKILL.md) | main | User or model |
| [`council`](../vendor/tstack/skills/council/SKILL.md) | main | User or model |
| [`file-pr`](../vendor/tstack/skills/file-pr/SKILL.md) | main | User or model |
| [`full-send`](../vendor/tstack/skills/full-send/SKILL.md) | main | User or model |
| [`full-stop`](../vendor/tstack/skills/full-stop/SKILL.md) | main | User or model |
| [`leaving-pr-comments`](../vendor/tstack/skills/leaving-pr-comments/SKILL.md) | main | User or model |
| [`modernize`](../vendor/tstack/skills/modernize/SKILL.md) | main | User or model |
| [`sol-loop`](../vendor/tstack/skills/sol-loop/SKILL.md) | main | User or model |
| [`takeover`](../vendor/tstack/skills/takeover/SKILL.md) | main | User or model |

## Matt Pocock (38)

| Skill | Bucket | Invocation |
| --- | --- | --- |
| [`ask-matt`](../vendor/matt-pocock/skills/engineering/ask-matt/SKILL.md) | engineering | User only |
| [`chief-of-staff`](../vendor/matt-pocock/skills/in-progress/chief-of-staff/SKILL.md) | beta | User only |
| [`claude-handoff`](../vendor/matt-pocock/skills/in-progress/claude-handoff/SKILL.md) | beta | User only |
| [`code-review`](../vendor/matt-pocock/skills/engineering/code-review/SKILL.md) | engineering | User or model |
| [`codebase-design`](../vendor/matt-pocock/skills/engineering/codebase-design/SKILL.md) | engineering | User or model |
| [`diagnosing-bugs`](../vendor/matt-pocock/skills/engineering/diagnosing-bugs/SKILL.md) | engineering | User or model |
| [`domain-modeling`](../vendor/matt-pocock/skills/engineering/domain-modeling/SKILL.md) | engineering | User or model |
| [`git-guardrails-claude-code`](../vendor/matt-pocock/skills/misc/git-guardrails-claude-code/SKILL.md) | misc | User or model |
| [`grill-me`](../vendor/matt-pocock/skills/productivity/grill-me/SKILL.md) | productivity | User only |
| [`grill-with-docs`](../vendor/matt-pocock/skills/engineering/grill-with-docs/SKILL.md) | engineering | User only |
| [`grilling`](../vendor/matt-pocock/skills/productivity/grilling/SKILL.md) | productivity | User or model |
| [`handoff`](../vendor/matt-pocock/skills/productivity/handoff/SKILL.md) | productivity | User only |
| [`implement`](../vendor/matt-pocock/skills/engineering/implement/SKILL.md) | engineering | User only |
| [`implement-spec`](../vendor/matt-pocock/skills/engineering/implement-spec/SKILL.md) | engineering | User only |
| [`improve-codebase-architecture`](../vendor/matt-pocock/skills/engineering/improve-codebase-architecture/SKILL.md) | engineering | User only |
| [`loop-me`](../vendor/matt-pocock/skills/in-progress/loop-me/SKILL.md) | beta | User only |
| [`matt-tdd`](../vendor/matt-pocock/skills/engineering/tdd/SKILL.md) | engineering | User or model |
| [`migrate-to-shoehorn`](../vendor/matt-pocock/skills/misc/migrate-to-shoehorn/SKILL.md) | misc | User or model |
| [`pr`](../vendor/matt-pocock/skills/engineering/pr/SKILL.md) | engineering | User or model |
| [`prototype`](../vendor/matt-pocock/skills/engineering/prototype/SKILL.md) | engineering | User or model |
| [`research`](../vendor/matt-pocock/skills/engineering/research/SKILL.md) | engineering | User or model |
| [`retro`](../vendor/matt-pocock/skills/engineering/retro/SKILL.md) | engineering | User only |
| [`scaffold-exercises`](../vendor/matt-pocock/skills/misc/scaffold-exercises/SKILL.md) | misc | User or model |
| [`setup-matt-pocock-skills`](../vendor/matt-pocock/skills/engineering/setup-matt-pocock-skills/SKILL.md) | engineering | User only |
| [`setup-pre-commit`](../vendor/matt-pocock/skills/misc/setup-pre-commit/SKILL.md) | misc | User or model |
| [`setup-ts-deep-modules`](../vendor/matt-pocock/skills/in-progress/setup-ts-deep-modules/SKILL.md) | beta | User only |
| [`teach`](../vendor/matt-pocock/skills/productivity/teach/SKILL.md) | productivity | User only |
| [`to-questionnaire`](../vendor/matt-pocock/skills/productivity/to-questionnaire/SKILL.md) | productivity | User only |
| [`to-spec`](../vendor/matt-pocock/skills/engineering/to-spec/SKILL.md) | engineering | User only |
| [`to-tickets`](../vendor/matt-pocock/skills/engineering/to-tickets/SKILL.md) | engineering | User only |
| [`triage`](../vendor/matt-pocock/skills/engineering/triage/SKILL.md) | engineering | User only |
| [`wait-what`](../vendor/matt-pocock/skills/productivity/wait-what/SKILL.md) | productivity | User only |
| [`wayfinder`](../vendor/matt-pocock/skills/engineering/wayfinder/SKILL.md) | engineering | User only |
| [`wizard`](../vendor/matt-pocock/skills/engineering/wizard/SKILL.md) | engineering | User or model |
| [`writing-beats`](../vendor/matt-pocock/skills/in-progress/writing-beats/SKILL.md) | beta | User only |
| [`writing-for-agents`](../vendor/matt-pocock/skills/productivity/writing-for-agents/SKILL.md) | productivity | User or model |
| [`writing-fragments`](../vendor/matt-pocock/skills/in-progress/writing-fragments/SKILL.md) | beta | User only |
| [`writing-shape`](../vendor/matt-pocock/skills/in-progress/writing-shape/SKILL.md) | beta | User only |

## Impeccable (1)

| Skill | Bucket | Invocation |
| --- | --- | --- |
| [`impeccable`](../vendor/impeccable/.agents/skills/impeccable/SKILL.md) | main | User or model |

## Ponytail (6)

| Skill | Bucket | Invocation |
| --- | --- | --- |
| [`ponytail`](../vendor/ponytail/skills/ponytail/SKILL.md) | main | User or model |
| [`ponytail-audit`](../vendor/ponytail/skills/ponytail-audit/SKILL.md) | main | User or model |
| [`ponytail-debt`](../vendor/ponytail/skills/ponytail-debt/SKILL.md) | main | User or model |
| [`ponytail-gain`](../vendor/ponytail/skills/ponytail-gain/SKILL.md) | main | User or model |
| [`ponytail-help`](../vendor/ponytail/skills/ponytail-help/SKILL.md) | main | User or model |
| [`ponytail-review`](../vendor/ponytail/skills/ponytail-review/SKILL.md) | main | User or model |

## Higgsfield (9)

| Skill | Bucket | Invocation |
| --- | --- | --- |
| [`higgsfield-brandkit`](../vendor/higgsfield/higgsfield-brandkit/SKILL.md) | main | User or model |
| [`higgsfield-faceless-video`](../vendor/higgsfield/higgsfield-faceless-video/SKILL.md) | main | User or model |
| [`higgsfield-generate`](../vendor/higgsfield/higgsfield-generate/SKILL.md) | main | User or model |
| [`higgsfield-marketplace-cards`](../vendor/higgsfield/higgsfield-marketplace-cards/SKILL.md) | main | User or model |
| [`higgsfield-product-photoshoot`](../vendor/higgsfield/higgsfield-product-photoshoot/SKILL.md) | main | User or model |
| [`higgsfield-soul-id`](../vendor/higgsfield/higgsfield-soul-id/SKILL.md) | main | User or model |
| [`higgsfield-video-explainer`](../vendor/higgsfield/higgsfield-video-explainer/SKILL.md) | main | User or model |
| [`higgsfield-websites`](../vendor/higgsfield/higgsfield-websites/SKILL.md) | main | User or model |
| [`higgsfield-youtube-thumbnail`](../vendor/higgsfield/higgsfield-youtube-thumbnail/SKILL.md) | main | User or model |

## WikiSkill (8)

| Skill | Bucket | Invocation |
| --- | --- | --- |
| [`script-exec-blocked`](../vendor/wikiskill/skills/script-exec-blocked/SKILL.md) | main | User or model |
| [`search-miss-binary`](../vendor/wikiskill/skills/search-miss-binary/SKILL.md) | main | User or model |
| [`spec-literal-execution`](../vendor/wikiskill/skills/spec-literal-execution/SKILL.md) | main | User or model |
| [`trace-harness-launch-failure`](../vendor/wikiskill/skills/trace-harness-launch-failure/SKILL.md) | main | User or model |
| [`verify-output-readback`](../vendor/wikiskill/skills/verify-output-readback/SKILL.md) | main | User or model |
| [`wikiskill-evolve`](../vendor/wikiskill/skills/wikiskill-evolve/SKILL.md) | main | User or model |
| [`wikiskill-maintainer`](../vendor/wikiskill/skills/wikiskill-maintainer/SKILL.md) | main | User or model |
| [`wikiskill-proposer`](../vendor/wikiskill/skills/wikiskill-proposer/SKILL.md) | main | User or model |

## Google Stitch design-md (1)

| Skill | Bucket | Invocation |
| --- | --- | --- |
| [`design-md`](../vendor/stitch-design-md/plugins/stitch-utilities/skills/design-md/SKILL.md) | main | User or model |
