"""Explicit local STT asset identity; no download, model load or device access."""

import hashlib
import json
from pathlib import Path

from victus.workflows.qualification_records import file_hash


def model_identity(directory):
    root = Path(directory).absolute()
    if not root.is_dir() or not all(
        (root / name).is_file() for name in ("model.bin", "config.json")
    ):
        raise ValueError("A complete local STT model directory is required")
    files = sorted(root.rglob("*"))
    if not 1 <= len(files) <= 128 or any(path.is_symlink() for path in files):
        raise ValueError("Bounded unlinked STT assets required")
    entries = [
        {"name": path.relative_to(root).as_posix(), "sha256": file_hash(path)}
        for path in files
        if path.is_file()
    ]
    return hashlib.sha256(json.dumps(entries, sort_keys=True).encode()).hexdigest()
