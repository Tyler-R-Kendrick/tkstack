# Shared programs

`scripts/` is the dotfiles installer. This directory holds the programs that
installer calls and that maintainers run directly:

- `tkstack.py` runs compiled skills and workflows.
- `tool.py` and `run_hook.py` launch pinned runtimes and native hooks.
- `check_docs.py` and `docs_hook.py` review documentation freshness.
- `tkstack_state.py` is the canonical state helper copied into each skill.
- `python_runtime.py`, `npm_runtime.py`, and `bootstrap_toolchains.py` install
  pinned language tools when setup asks for them.
- `setup_lever.py` installs Lever's Copilot project layout.

Run them as `python3 src/<name>.py`.
