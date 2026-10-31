"""Committed skill package roots: developed skills and third-party-derived packages."""

from pathlib import Path

# Root `skills/` is reserved for skills under active development. Packages derived
# from or wrapping outside sources live in the harness-independent `.agents/skills/`.
DEVELOPED = Path("skills")
ADOPTED = Path(".agents/skills")


def packages(root, relative):
    """Real (non-link) package directories; installed links in the same tree are skipped."""
    directory = Path(root) / relative
    if directory.is_symlink() or not directory.is_dir():
        return {}
    return {path.name: path for path in sorted(directory.iterdir())
            if not path.is_symlink() and (path / "SKILL.md").is_file()}


def all_packages(root):
    """Every committed package by name; a name may exist in only one root."""
    developed, adopted = packages(root, DEVELOPED), packages(root, ADOPTED)
    if shared := set(developed) & set(adopted):
        raise ValueError("Skill package in both roots: " + ", ".join(sorted(shared)))
    return {**developed, **adopted}
