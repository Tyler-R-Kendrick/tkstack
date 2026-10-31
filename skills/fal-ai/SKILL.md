---
name: fal-ai
description: Plan and produce images, video, audio, brand assets, and product media with explicit deliverables and actual output inspection. Use for fal.ai or a provider-neutral media production brief. Preserve explicit Higgsfield or other provider selections and use their real adapters.
license: MIT
compatibility: "Portable Markdown production workflow. Actual generation needs the selected provider tools, credentials, supported model, and authorized budget. Typed contract tools require Python 3.11+ and the managed command-schema runtime."
metadata:
  author: Tyler Kendrick
  version: "0.3.0"
---

# Media production and fal.ai

<!-- tkstack:execution:start -->
Tool: `.tkstack/tkstack skills fal-ai -- <command>`. Omit the command for deterministic man-page help.

| Executable operation | Contract |
| --- | --- |
| Default/help and man(1) export | [Reserved help](commands/help.md) |
| Declared package version | [Reserved version](commands/version.md) |
| `model` | [Typed parameters](commands/model.md) |
| `verify` | [Typed parameters](commands/verify.md) |
| Evidence, effects, native execution, and semantic boundaries | [Execution contract](references/execution.md) |

`model` reads the explicit contract; `verify` checks retained facts/evidence. Native commands execute existing code. Residual semantic decisions use the focused procedures below; a recorded review is not an independently authenticated judgment.
<!-- tkstack:execution:end -->


Preserve the user's provider, model, budget, reference material, and format.
An explicit fal.ai request uses fal; an explicit other-provider request does not.

| Work | Read before acting |
| --- | --- |
| Brief, image/product/brand/thumbnail/video planning, or output inspection | [Media production](references/media-production.md) |
| Discover models, submit, poll, or retrieve through fal | [fal adapter](references/fal-adapter.md) |

Resolve the deliverable from supplied context. Inspect current schemas and
pricing before a real job. Setup/discovery alone does not authorize generation.
Submit once, retain endpoint/request IDs, recover unknown jobs before retrying,
and report only terminal completed outputs as complete.

Use actual artifact inspection for quality and fidelity; URLs and job status
are insufficient. Provider-native identity training and studio workflows stay
with their actual adapters. See [sources](references/distilled-sources.md).

For session/repository/workspace records, read [local state storage](references/storage.md).
