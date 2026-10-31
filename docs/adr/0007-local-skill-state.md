# Keep skill state under .tkstack with local ignore protection

Status: accepted. Date: 2026-10-30.

All custom skills store session/repository/workspace bookkeeping under a
`.tkstack/` directory with its own `.gitignore`. Raw learning histories, evidence,
handoffs, plans, leases, locks, caches, and run results persist locally across
sessions and remain outside source control. Durable reuse discovery metadata
is `.tkstack/reuse/catalog.json`; the policy and that catalog can be versioned.
Authored code, reusable assets, instructions, and product/repository documentation
retain their native or explicitly requested locations.

Move existing learning data intact and migrate installer-owned steering aliases.
Preserve foreign configuration and reject conflicting paths. Standalone skills
use the active project; explicitly configured shared aliases may continue to
share a `.tkstack/` store across harnesses. A fresh clone initializes empty
local views and reads packaged standards/seeds rather than distributing private
session records. This changes the Git-persistence consequence of ADR 0002 and
the catalog location in ADR 0005.

One shared deterministic state primitive computes paths, guards containment,
initializes ignore rules, and coordinates policy writers. Bundle byte-identical
copies in each portable custom package. Read-only operations do not initialize
state. Reject private writes outside `.tkstack/` or through escaping symlinks.
Keep worktree/cache/build roots inside an appropriate workspace `.tkstack/`
while preserving the requirement to stay outside registered checkouts.

Verify visibility with native Git, including policy/catalog inclusion and
session/history/cache exclusion. Preserve local records on uninstall; source
control exclusion does not mean deleting local learning between sessions.
