"""Safe prerequisite reporting and offline, instance-locked maintenance commands."""

import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path

import httpx

from victus.runtime.paths import dashboard_root
from victus.storage.backups import Backups, offline_guard, restore
from victus.storage.migrations import _discover_migrations, current_version, migrate


def version():
    return importlib.metadata.version("victus-assistant")


def prerequisites(settings):
    try:
        with httpx.Client(timeout=0.5, trust_env=False, follow_redirects=False) as client:
            r = client.get("http://127.0.0.1:11434/api/tags")
            ollama = "reachable_model_not_verified" if r.status_code == 200 else "unavailable"
    except Exception:
        ollama = "unavailable"
    browser = "not_installed"
    local = os.getenv("LOCALAPPDATA")
    configured = os.getenv("PLAYWRIGHT_BROWSERS_PATH")
    roots = [Path(configured)] if configured and configured != "0" else []
    if local:
        roots.append(Path(local) / "ms-playwright")
    # Presence is not browser-control qualification and no engine is downloaded.
    for root in roots:
        if root.is_dir() and any(root.glob("chromium-*/chrome-win*/chrome.exe")):
            browser = "files_present_control_not_verified"
    model = settings.voice_model_path
    voice = ("local_asset_present_audio_not_verified" if model and model.is_dir()
             and (model / "model.bin").is_file() else "local_model_not_configured_or_missing")
    libraries = all(importlib.util.find_spec(name) is not None
                    for name in ("faster_whisper", "sounddevice"))
    return {
        "version": version(), "data_dir": str(settings.data_dir),
        "token_configured": len(settings.api_token) >= 32,
        "dashboard": "installed" if (dashboard_root() / "index.html").is_file() else "missing_build",
        "ollama": ollama,
        "ollama_message": "Install/start Ollama and qualify an explicitly pinned local model.",
        "browser": browser,
        "browser_message": "Install the matching Playwright Chromium engine separately; no bundled browser session.",
        "voice": voice, "voice_libraries": libraries,
        "voice_message": "Configure a previously downloaded local STT asset; microphone use requires explicit input.",
        "wake": "off_until_explicitly_enabled", "autostart": "not_installed",
        "cloud": "disabled" if not settings.cloud_model else "requires_exact_transfer_consent",
    }


def maintain(command, settings, source=None, destination=None):
    if command == "backup":
        if destination is None:
            raise ValueError("Backup requires --destination")
        return Backups(settings.data_dir, lambda: offline_guard(settings.data_dir)).create(destination)
    if command == "restore":
        if source is None or destination is None:
            raise ValueError("Restore requires --source and a new --destination")
        return restore(source, destination)
    if command == "migrate":
        root = settings.data_dir
        if not root.is_dir():
            raise ValueError("Migration requires an existing stopped data directory")
        with offline_guard(root):
            path = root / "victus.sqlite3"
            existing = current_version(path)
            supported = max(n for n, _ in _discover_migrations())
            if existing and existing > supported:
                raise ValueError("Database schema is newer than this application; restore a compatible backup")
            applied = migrate(path)
            return {"applied": applied, "schema": current_version(path)}
    raise ValueError("Unsupported maintenance command")


def print_result(value):
    print(json.dumps(value, indent=2))
