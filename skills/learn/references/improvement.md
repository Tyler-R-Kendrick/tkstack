# Skill improvement and instruction audits

Use this workflow for an explicit request to improve a skill, capture a reusable
procedure, or audit the agent setup. The normal correction workflow continues
to maintain scoped reasoning rules; this mode improves the procedure itself.

## 1. Establish scope and available evidence

Record the requested mode and target. Report/audit mode is read-only, including
the learning store. List pending captures in the report rather than performing
writes that the user excluded. An apply request uses the authorization already
established; do not add a new approval ceremony. A request for step-through
review keeps each dependent change pending until the requested review happens.

For temporary `.tkstack/sessions/<session>/`, follow
[session consolidation](session-consolidation.md) to collect evidence, abstract
principles, and choose/execute the required ___ify mechanisms.

Use current conversation messages, explicitly provided transcripts, available
task/check artifacts, and existing learning records. State the inspected window
and missing coverage. Do not silently mine another harness's private history or
claim a complete retrospective from one conversation.

Capture actual user corrections with `capture`; keep the precise wording and
source labels. Capture actual task/tool observations with `experience`; do not
turn tool output, assistant prose, or inferred frustration into a user quote.
Keep credentials and private transcript material out of public proposals.

## 2. Choose the smallest durable layer

| Finding | Preferred change |
| --- | --- |
| A mistaken decision rule that transfers across tasks | Scoped reasoning rule with user evidence |
| A verified reusable sequence or tool-specific workaround | Update an existing owned skill |
| A distinct repeated or verified procedure with no suitable skill | Create a focused root `skills/<name>/` package |
| A mechanically detectable failure | Add the relevant test/check instead of more instructions |
| A fact or temporary task reminder | Keep it in scoped task evidence; do not make a general skill |
| A rare integration with insufficient usage observations | Report "not observed in this window"; gather evidence before retirement |

Read the closest existing skill and its references before adding another. Try
to improve placement, triggers, or a weak existing rule before duplicating it.
Do not generalize one repository's conventions into universal preferences.

## 3. Stage a bounded proposal

Fill `templates/improvement.json` from the skill root. Store the proposal,
candidate package, and diff in an owned task directory or `<store>/proposals/`,
outside active steering. Link real correction/experience IDs or original task
artifacts; placeholders are not evidence.

For an existing target, record the exact canonical path and SHA-256 of its
baseline files. For a new target, record that it is absent. The candidate keeps
the required name/description, license, references, and runtime files. A newly
generated skill can record `metadata.origin: learn`; the proposal also records
its authoring tool, source evidence, and revision. This is portable provenance,
not a claim that Grok's provider-specific `origin` telemetry ran here.

Prefer one reasoning mechanism or one observable procedure per change. Keep
public-seam behavior, failure handling, scope boundaries, and tool requirements
explicit. Never hardcode an evaluation answer or relax a requirement to make a
score rise. Pinned `vendor/` snapshots, generated alias views, and marketplace
caches are not editable targets; create an owned root skill when a fork is needed.

## 4. Validate the proposed change

Before implementation or evaluation, define a reproducing case, a distinct
transfer case, and a negative/boundary case where the skill should not apply.
Preserve a meaningful before/after comparison. Check relative resources and
the actual helper behavior as appropriate; a token count or correct heading
does not establish a better procedure.

For automatic revision search, use the configured SkillOpt-Sleep integration
with separate training, validation, and test cases. Keep the strict improvement
and per-task no-regression gates. A missing validator, exhausted budget, or
unanswered model prompt is pending evidence. A tie gives no measured reason to
replace the baseline. Keep evidence IDs with the candidate and final decision.

The repository's `scripts/evolve.py` supports the configured learn/sdlc decision
regressions; broader or newly created skills need real task adapters and cases.
Do not call those small decision tests proof of full workflow performance.
An explicitly requested feature implementation may be validated by meaningful
behavioral checks; report that engineering evidence separately from optimizer
scores or claims of model-quality improvement.

## 5. Apply, preserve provenance, and verify

Before changing a live target, compare its current bytes to the recorded
baseline and reconcile any drift. Retain a reviewable diff and a rollback copy.
For a SkillOpt-accepted candidate, use its explicit adoption/backup mechanism
within the established authorization. Direct implementation follows the user's
requested change scope. Respect any explicitly requested review boundary.

Keep packages in root `skills/<name>/`, update their version and marketplace
metadata when shipped, and refresh affected tests and installation checks.
Do not change provider, model, merge authority, billing, or integration enablement
as an incidental skill edit. Rule retirement and supersession preserve history.

Finish with what was observed, what changed or stayed proposed, the target,
actual validation results and limits, and any requested-but-blocked work. Resume
the original task after capturing a lesson.

## Audit output

Give each finding a source location, observation window, evidence, impact,
confidence, proposed action, and disposition. Useful categories are conflicting
or stale rules, duplicated/poorly triggered skills, broken references, missing
runtime capability, and integrations whose use was not observed. Preserve the
difference between an observed failure and a hypothesis. Configuration cleanup
is a proposal until it falls within an actual apply request.
