# Optional OpenWiki adapter

Use this branch only with the real OpenWiki tools and an explicit wiki request.
Prefer its installed official skill for the exact current schema and lifecycle.
Resolve the absolute Git root and inspect whether the request is `init` or
`update`. Init replaces generated pages; choose update for incremental refresh.
Do not infer destructive regeneration from a vague documentation request.

The lifecycle is begin, plan when requested, next assigned page, submit that
page and its sparse Claim decisions, repeat, then finish. Continue the durable
queue returned by begin. Noop means no update is needed. Source drift requires
a new valid plan; do not reuse the invalidated one.

Only write the assigned page during the page loop. Research its source and
preserve accurate unaffected claims. OpenWiki owns Claim IDs, sidecars,
indexes, provenance, run metadata, and finalization; do not edit those by hand.
Success requires the actual finish result to report complete.

For retrieval, search a concrete question, then read the exact returned page
sections. If workspace selection is ambiguous, resolve it from the request or
ask the user; do not silently search a different workspace. Stop once grounded.

If tools are absent, use ordinary Markdown maintenance and report that boundary.
An equivalent-looking file tree is not a completed OpenWiki lifecycle. Native
host generation uses the agent's session; standalone generation has separate
provider configuration. This reference neither installs nor authenticates it.
