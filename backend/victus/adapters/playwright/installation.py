"""Resolve the locked Chromium installation without starting a driver or browser."""

import json
import os
import sys
from pathlib import Path

import playwright

from victus.workflows.qualification_records import file_hash


def chromium_executable() -> Path:
    package = Path(playwright.__file__).parent / "driver/package"
    descriptor = package / "browsers.json"
    file_hash(descriptor)
    entries = json.loads(descriptor.read_text(encoding="utf-8"))["browsers"]
    matches = [entry for entry in entries if entry.get("name") == "chromium"]
    if len(matches) != 1:
        raise ValueError("One installed Chromium descriptor required")
    revision = matches[0]["revision"]
    if not isinstance(revision, str) or not revision.isascii() or not revision.isdecimal():
        raise ValueError("Invalid Chromium revision")
    override = os.getenv("PLAYWRIGHT_BROWSERS_PATH")
    if override == "0":
        cache = package / ".local-browsers"
    elif override:
        cache = Path(override)
        if not cache.is_absolute():
            raise ValueError("An absolute browser cache is required")
    elif sys.platform == "win32":
        cache = Path(os.environ["LOCALAPPDATA"]) / "ms-playwright"
    elif sys.platform.startswith("linux"):
        cache = Path(os.getenv("XDG_CACHE_HOME") or Path.home() / ".cache") / "ms-playwright"
    else:
        raise ValueError("This qualified browser layout supports Windows and Linux only")
    if not cache.is_absolute():
        raise ValueError("An absolute browser cache is required")
    if sys.platform == "win32":
        binary = cache / f"chromium-{revision}" / "chrome-win64/chrome.exe"
    elif sys.platform.startswith("linux"):
        binary = cache / f"chromium-{revision}" / "chrome-linux64/chrome"
    else:
        raise ValueError("Unsupported qualified browser platform")
    # Checks every ancestor and rejects missing files, symlinks and reparse points.
    file_hash(binary)
    return binary
