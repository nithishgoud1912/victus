"""Read-only, exact unsigned bundle integrity checks; no capability promotion."""

import hashlib
import re
from pathlib import Path

from victus.workflows.qualification_records import _verify_frozen_files, read_record


def verify_bundle(directory):
    root = Path(directory).absolute()
    manifest_path = root / "release-manifest.json"
    manifest, digest = read_record(manifest_path, maximum=16 * 1024 * 1024)
    if (
        manifest.get("bundle") != "windows-x64-onedir"
        or manifest.get("format") != 1
        or not isinstance(manifest.get("source_sha256"), str)
        or not re.fullmatch(r"[a-f0-9]{64}", manifest["source_sha256"])
    ):
        raise ValueError("Source-bound Windows folder manifest required")
    _verify_frozen_files(root, manifest, digest)
    expected = {item["path"] for item in manifest["files"]} | {"release-manifest.json"}
    actual = set()
    for path in root.rglob("*"):
        status = path.lstat()
        if path.is_symlink() or getattr(status, "st_file_attributes", 0) & 0x400:
            raise ValueError("Linked bundle entry rejected")
        if path.is_file():
            actual.add(path.relative_to(root).as_posix())
    if actual != expected or "Victus.exe" not in actual:
        raise ValueError("Bundle inventory differs from manifest")
    if hashlib.sha256(manifest_path.read_bytes()).hexdigest() != digest:
        raise ValueError("Bundle manifest changed during verification")
    return {
        "source_sha256": manifest["source_sha256"],
        "bundle_manifest_sha256": digest,
        "files_verified": len(manifest["files"]),
        "integrity_verified": True,
        "release_qualified": False,
    }
