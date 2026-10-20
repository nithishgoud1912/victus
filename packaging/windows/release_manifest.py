"""Checksums and dependency inventory, without host paths, user data or secrets."""

import hashlib
import importlib.metadata
import json
import os
import sys
from pathlib import Path

from victus.runtime.source_inventory import verify_source_inventory


def create(root):
    root = root.resolve(strict=True)
    if (root / "release-manifest.json").exists():
        raise FileExistsError("Existing bundle manifest is immutable")
    files = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or getattr(path.lstat(), "st_file_attributes", 0) & 0x400:
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
            path.suffix.lower()
            in {
                ".sqlite3",
                ".sqlite",
                ".db",
                ".wav",
                ".flac",
                ".mp3",
                ".ogg",
                ".pcm",
                ".tflite",
                ".gguf",
                ".safetensors",
                ".pt",
                ".pth",
            }
            or (path.suffix.lower() == ".onnx" and not small_vad)
            or path.name.lower() in {"model.bin", "credentials.json", "token.txt"}
            or path.name.lower().endswith(
                (".sqlite3-wal", ".sqlite3-shm", ".db-wal", ".db-shm")
            )
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
        source_path = Path(os.environ["VICTUS_BUILD_SOURCE_MANIFEST"])
        verify_source_inventory(
            source_path, Path(__file__).resolve().parents[2], require_complete=True
        )
        source = json.loads(source_path.read_text())
        result["source_sha256"] = source["source_sha256"]
        result["git_base"] = source["base_revision"]
    with (root / "release-manifest.json").open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    if not os.getenv("VICTUS_BUILD_SOURCE_MANIFEST"):
        raise ValueError("Windows builds require a verified source manifest")
    result = create(Path(sys.argv[1]))
    print(f"Checksummed {len(result['files'])} release files")
