# Separate procedural experience from user authority

Status: accepted. Date: 2026-10-29 (America/Chicago).

The user wants Grok Build-style skill improvement incorporated into `learn`.
The checked public Grok tree exposes runtime skill delivery and provenance,
but not the learn prompt, so the implementation must state its source limits.

Extend the existing portable store with typed task/tool `experience` events and
derived candidate-lesson pages. Preserve the user-correction collection and its
rule-evidence requirement. Experience IDs cannot authorize active rules, and
experience pages stay outside startup steering.

Add explicit read-only report/audit modes and a bounded skill-improvement
workflow with provenance, baseline/diff, validation, and rollback. Automatic
correction capture alone does not authorize skill/configuration edits. Keep the
selected SkillOpt gate for automatic revisions and treat direct feature tests
as engineering evidence rather than measured improvement in model behavior.

The exact Grok body remains discoverable only if an authorized runtime/cache
actually supplies it. A read-only locator reports candidate paths and checksum
status without fetching a bundle, exposing credentials, or running the skill.
