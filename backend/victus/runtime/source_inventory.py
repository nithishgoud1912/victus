"""Validate captured source identities against exact repository bytes."""

import hashlib
import json
import re
from pathlib import Path, PurePosixPath

from victus.workflows.qualification_records import file_hash, read_record


def verify_source_inventory(manifest_path, repository, *, require_complete=False):
    record, _ = read_record(manifest_path, maximum=16 * 1024 * 1024)
    entries = record.get("files")
    if not isinstance(entries, dict) or not 1 <= len(entries) <= 20000:
        raise ValueError("Bounded source file inventory required")
    root = Path(repository).absolute()
    for name, entry in entries.items():
        relative = PurePosixPath(name)
        if (
            not name
            or "\\" in name
            or ":" in name
            or relative.is_absolute()
            or ".." in relative.parts
            or relative.as_posix() != name
            or not isinstance(entry, dict)
            or set(entry) != {"sha256", "bytes"}
            or type(entry["bytes"]) is not int
            or entry["bytes"] < 0
            or not isinstance(entry["sha256"], str)
            or not re.fullmatch(r"[a-f0-9]{64}", entry["sha256"])
        ):
            raise ValueError("Malformed source inventory")
        path = root.joinpath(*relative.parts)
        if file_hash(path) != entry["sha256"] or path.stat().st_size != entry["bytes"]:
            raise ValueError("Captured source file changed")
    digest = hashlib.sha256(
        json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    if digest != record.get("source_sha256"):
        raise ValueError("Source inventory digest mismatch")
    if require_complete and entries != capture_entries(root):
        raise ValueError("Source inventory omits or adds release inputs")
    return digest


def capture_entries(repository):
    """Inventory release inputs, including new untracked source, using Git scope."""
    import subprocess

    root = Path(repository).absolute()
    names = (
        subprocess.check_output(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=root
        )
        .decode()
        .split("\0")
    )
    scopes = (
        "backend/victus/",
        "backend/tests/",
        "dashboard/src/",
        "dashboard/scripts/",
        "config/",
        "contracts/",
        "scripts/",
        "packaging/",
        "evaluation/",
    )
    extras = {
        "backend/pyproject.toml",
        "backend/uv.lock",
        "backend/.python-version",
        "dashboard/package.json",
        "dashboard/package-lock.json",
        "dashboard/openapi.json",
        "dashboard/index.html",
    }
    entries = {}
    for name in sorted(set(names)):
        if not name or not (
            name.startswith(scopes)
            or name in extras
            or (
                name.startswith("dashboard/")
                and "/" not in name[10:]
                and Path(name).suffix in {".json", ".ts", ".js"}
            )
        ):
            continue
        if (
            any(
                part in {".local", ".venv", "__pycache__", "node_modules"}
                for part in Path(name).parts
            )
            or ".env" in Path(name).name
        ):
            continue
        path = root / name
        if not path.is_file():
            raise ValueError("Release input missing")
        entries[name] = {"sha256": file_hash(path), "bytes": path.stat().st_size}
    if not entries:
        raise ValueError("Release inputs unavailable")
    return entries


def source_identity(repository):
    return hashlib.sha256(
        json.dumps(capture_entries(repository), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
