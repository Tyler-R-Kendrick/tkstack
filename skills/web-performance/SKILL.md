---
name: web-performance
description: Improve web performance with Chrome Modern Web Guidance and agent-browser vitals in a bounded, measured loop. Use for web performance optimization or as part of SDLC web implementation when rendering or loading can change. Compare actual browser measurements and preserve behavior and accessibility.
license: MIT
compatibility: "Requires Node.js, agent-browser with a compatible browser, and the project's runnable web app. Modern Web Guidance is retrieved with its npm CLI."
metadata:
  author: Tyler Kendrick
  version: "0.1.0"
  kind: guidance
---

# Web performance

Use this skill for a real web page and representative routes, including SDLC
web changes that can affect loading, rendering, or interaction. Scope the work
to the requested task; a documentation-only change or an unaffected API does
not require a browser optimization run. Installing this skill runs nothing.

1. Start the project's actual app or production preview and choose representative
   URLs, viewport, browser, network and cache state, and relevant user journeys.
   Record versions and conditions. Use an isolated browser session and keep
   measurements serial when contention would affect timing.
2. Read the installed browser's `agent-browser skills get modern-web-guidance`.
   Retrieve the applicable Chrome guidance, for example:

   ```sh
   npx modern-web-guidance@latest retrieve "performance" > performance-guide.md
   agent-browser vitals http://localhost:3000/ --json > baseline.json
   ```

   Read the whole guide and record its version and applicable rule IDs. Resolve
   and hold tool versions fixed for a comparison; `latest` can change. Use the
   actual served URL: a source directory is not a page URL. Browser setup is
   separate (`agent-browser install` if necessary). Do not install globally or
   modify a project dependency without an appropriate reason.
3. Establish repeated unchanged baseline samples and inspect the JSON and real
   page. Freeze the route, workload, environment, metric, actionable threshold,
   budget and behavior/accessibility guardrails. Treat missing metrics as
   unavailable, not zero. `vitals` measures a page load; interaction-dependent
   INP needs representative interactions and suitable measurement, and a lab
   sample is not a field Core Web Vitals distribution.
4. Form one hypothesis from observed evidence and applicable guidance; change
   the project source, inspect its diff, and rerun the same repeated browser
   measurement and behavior checks. For example, reserve image space with
   accurate dimensions; use `content-visibility` on suitable offscreen complex
   content with a content-derived `contain-intrinsic-size`. Do not apply either
   blindly. Inspect layout, responsive states, interactions and accessibility.
5. Retain a change only when the relevant metric improves beyond baseline noise
   and the practical threshold while required guardrails pass. Keep failed and
   inconclusive results, and confirm the fixed candidate on fresh representative
   cases where feasible. Cite guide IDs, source revisions, commands, conditions,
   samples, and actual outputs. A source diff is not a performance measurement.

A missing browser, server, guide, representative workload, or metric means the
corresponding result is unverified; report the gap rather than claiming a win.
The optional `hill-climb` skill can coordinate bounded experiments when installed.
Chrome's [Modern Web Guidance](https://developer.chrome.com/docs/modern-web-guidance)
and the version-matched agent-browser skill are the sources for the tool usage;
this package is independent guidance, not a bundled copy of either tool.
