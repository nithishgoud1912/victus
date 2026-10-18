"""Capture a fresh private source/config/contracts/lock inventory without runtime payloads."""

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCOPES = (
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
EXTRAS = {
    "backend/pyproject.toml",
    "backend/uv.lock",
    "backend/.python-version",
    "dashboard/package.json",
    "dashboard/package-lock.json",
    "dashboard/openapi.json",
    "dashboard/index.html",
}


def git(*arguments):
    return subprocess.check_output(["git", *arguments], cwd=ROOT)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-directory", type=Path, required=True)
    args = parser.parse_args()
    output = args.output_directory.resolve()
    output.mkdir(parents=True, exist_ok=False)
    paths = (
        git("ls-files", "-z", "--cached", "--others", "--exclude-standard")
        .decode()
        .split("\0")
    )
    entries = {}
    for name in sorted(set(paths)):
        path = ROOT / name
        if not name or not path.is_file() or path.is_symlink():
            continue
        if not (
            name in EXTRAS
            or name.startswith(SCOPES)
            or (
                name.startswith("dashboard/")
                and "/" not in name[10:]
                and path.suffix in {".json", ".ts", ".js"}
            )
        ):
            continue
        if (
            any(
                part in {".local", ".venv", "__pycache__", "node_modules"}
                for part in path.parts
            )
            or ".env" in path.name
        ):
            continue
        data = path.read_bytes()
        entries[name] = {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
    manifest = {
        "base_revision": git("rev-parse", "HEAD").decode().strip(),
        "files": entries,
    }
    manifest["source_sha256"] = hashlib.sha256(
        json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    (output / "source.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (output / "dirty-status.txt").write_bytes(
        git("status", "--short", "--untracked-files=all")
    )
    roots = {
        "configured_data_dir": os.getenv("VICTUS_DATA_DIR"),
        "environment_default_data_dir": str(Path(os.environ["LOCALAPPDATA"]) / "VICTUS")
        if os.getenv("LOCALAPPDATA")
        else None,
        "selected_user_runtime": None,
        "test_root": str(output),
        "prior_test_roots_preserved": True,
    }
    (output / "runtime-roots.json").write_text(json.dumps(roots, indent=2) + "\n")
    print(
        json.dumps(
            {
                "source_sha256": manifest["source_sha256"],
                "files": len(entries),
                "user_runtime_selected": False,
            }
        )
    )


if __name__ == "__main__":
    main()
