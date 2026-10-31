"""Resolve native host configuration without redirecting isolated install targets."""
import os
from pathlib import Path


def codex_directory(target, scope):
    if scope == 'home' and target.resolve() == Path.home().resolve() and os.environ.get('CODEX_HOME'):
        return Path(os.environ['CODEX_HOME']).expanduser().absolute()
    return target / '.codex'
