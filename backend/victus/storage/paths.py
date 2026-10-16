"""Artifact paths are data-root-relative and never follow symlinks/reparse points."""

from pathlib import Path, PurePosixPath


def safe_path(root: Path, relative: str, *, prefix=None):
    if not isinstance(relative, str) or "\\" in relative or ":" in relative:
        raise ValueError("Invalid retained path")
    parts = PurePosixPath(relative).parts
    if not parts or PurePosixPath(relative).is_absolute() or any(x in {".", ".."} for x in parts):
        raise ValueError("Unsafe retained path")
    if prefix is not None and parts[0] != prefix:
        raise ValueError("Artifact is outside its retained directory")
    current = root
    for part in (None, *parts):
        if part is not None:
            current = current / part
        if current.is_symlink() or (hasattr(current, "is_junction") and current.is_junction()):
            raise ValueError("Linked artifact paths are not supported")
        if current.exists() and getattr(current.stat(), "st_file_attributes", 0) & 1024:
            raise ValueError("Reparse artifact paths are not supported")
    if not current.resolve().is_relative_to(root.resolve()):
        raise ValueError("Artifact escaped data root")
    return current
