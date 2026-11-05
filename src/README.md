# Shared programs

`scripts/install.py` is the linker `install.sh` execs. This directory holds the
programs the repository runs directly:

- `tkstack.py` runs compiled skills and workflows.
- `check_docs.py` checks the documentation ledger. `check_skills.py` checks owned skill contracts.
- `tkstack_state.py` is the canonical state helper copied into each skill.
- `skill_roots.py` lists owned skill packages.

Skill-owned programs live with those skills: `skills/sdlc/scripts/routing_inventory.py`, `skills/learn/scripts/evolve.py`, and `skills/learn/skills/skillify/scripts/sync_codify.py`. SDLC runs the routing inventory. The root skills gate does not. Importing `routing_inventory.py` does not load `scripts/install.py` or `skill_roots.py`; the check loads those when it runs. `evolve.py` and `sync_codify.py` do not import the repository root.

Run a program here as `python3 src/<name>.py`.
