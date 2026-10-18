"""Checksums and dependency inventory, without host paths, user data or secrets."""

import hashlib
import importlib.metadata
import json
import os
import sys
from pathlib import Path


def create(root):
    root = root.resolve(strict=True)
    files = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("Release symlink is not allowed")
        if not path.is_file() or path.name == "release-manifest.json":
            continue
        relative = path.relative_to(root).as_posix()
        small_vad = (
            relative.startswith("_internal/faster_whisper/assets/")
            and path.suffix == ".onnx"
            and path.stat().st_size < 5 * 1024**2
        )
        if (
            path.suffix.lower() in {".sqlite3", ".wav", ".flac", ".tflite"}
            or (path.suffix.lower() == ".onnx" and not small_vad)
            or path.name.startswith(".env")
            or "browser_profiles" in path.parts
        ):
            raise ValueError("Release includes a private or large external asset")
        with path.open("rb") as stream:
            sha = hashlib.file_digest(stream, "sha256").hexdigest()
        files.append({"path": relative, "bytes": path.stat().st_size, "sha256": sha})
    result = {
        "format": 1,
        "version": importlib.metadata.version("victus-assistant"),
        "bundle": "windows-x64-onedir",
        "elevation": "asInvoker",
        "autostart": False,
        "listening_after_install": False,
        "signing": "unsigned-local-candidate",
        "dependencies": sorted(
            {
                d.metadata["Name"]: d.version
                for d in importlib.metadata.distributions()
            }.items()
        ),
        "files": files,
    }
    if os.getenv("VICTUS_BUILD_SOURCE_MANIFEST"):
        source = json.loads(
            Path(os.environ["VICTUS_BUILD_SOURCE_MANIFEST"]).read_text()
        )
        result["source_sha256"] = source["source_sha256"]
        result["git_base"] = source["base_revision"]
    (root / "release-manifest.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    result = create(Path(sys.argv[1]))
    print(f"Checksummed {len(result['files'])} release files")
