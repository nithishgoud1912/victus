"""Explicit portable toolchain selection for local browser regression runners.

An alternate browser is reported by identity. It never qualifies the pinned
production engine or changes application capability registration.
"""

import hashlib
import importlib.metadata
import json
import os
import shutil
import subprocess
from pathlib import Path


def creation_flags():
    return subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


def node_executable(root):
    override = os.getenv("VICTUS_TEST_NODE")
    candidate = (
        Path(override) if override else root / ".local/toolchains/node-v24.22.0-win-x64/node.exe"
    )
    if candidate.is_absolute() and candidate.is_file():
        return str(candidate)
    if override:
        raise ValueError("Explicit test Node executable is missing or not absolute")
    found = shutil.which("node")
    if found is None:
        raise RuntimeError("Test Node executable unavailable")
    return found


def launch_browser(playwright, **options):
    configured = os.getenv("VICTUS_TEST_BROWSER_EXECUTABLE")
    executable = Path(configured) if configured else None
    if executable is not None:
        if not executable.is_absolute() or not executable.is_file():
            raise ValueError("Explicit test browser must be an existing absolute executable")
        options["executable_path"] = str(executable)
    browser = playwright.chromium.launch(**options)
    destination = os.getenv("VICTUS_TEST_BROWSER_METADATA")
    if destination:
        try:
            metadata = {
                "browser_version": browser.version,
                "playwright_version": importlib.metadata.version("playwright"),
                "explicit_alternate_binary": executable is not None,
                "production_qualification": False,
            }
            if executable is not None:
                with executable.open("rb") as stream:
                    metadata["binary_sha256"] = hashlib.file_digest(stream, "sha256").hexdigest()
            with Path(destination).open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(metadata) + "\n")
        except BaseException:
            browser.close()
            raise
    return browser
