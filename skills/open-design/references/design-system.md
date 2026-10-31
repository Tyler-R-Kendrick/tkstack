# Capture a useful design system

Inspect actual rendered examples alongside source styles, tokens, and component
behavior. Record conflicts between captures and code rather than choosing a
filename as visual authority. Prefer a small representative set over an exhaustive
inventory of every CSS value.

Write `DESIGN.md` or the project's existing canonical system document with the
surface's purpose, visual character, semantic color roles and actual values,
type hierarchy, spacing/layout rules, reusable components, responsive states,
accessibility requirements, and image/motion conventions. Separate observed
rules from a proposed new direction.

Describe semantic intent as well as literals: a warning color has a meaning,
not just a hex code. Include the conditions that choose a component or variant.
Use linked detailed references for exceptional surfaces instead of making every
screen load the entire system.

Preserve authored rules and document only within scope. For Stitch requests,
use the actual authorized project/screens and returned assets through available
tools. Missing Stitch access cannot establish that a project's palette or
layout was extracted. For another provider, keep the same documentation outcome
without copying Stitch-specific tool calls.
