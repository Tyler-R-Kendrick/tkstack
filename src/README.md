# Shared programs

`scripts/install.py` is the linker `install.sh` execs. This directory holds the
programs the repository runs directly:

- `tkstack.py` runs compiled skills and workflows.
- `check_docs.py` checks the documentation ledger. `check_skills.py` checks owned skill contracts and the SDLC routing inventory.
- `tkstack_state.py` is the canonical state helper copied into each skill.
- `skill_roots.py` lists owned skill packages.

Skill-owned programs live with those skills: `skills/sdlc/scripts/routing_inventory.py`, `skills/learn/scripts/evolve.py`, and `skills/learn/skills/skillify/scripts/sync_codify.py`. `routing_inventory.py` is still exec'd by the root skills gate (`src/check_skills.py`). It imports `scripts/install.py` and `skill_roots.py` and inventories every skill, vendor tree, and harness, so the move colocates the check with SDLC's `skill-routing.md`. `evolve.py` and `sync_codify.py` do not import the repository root.

Run a program here as `python3 src/<name>.py`.
