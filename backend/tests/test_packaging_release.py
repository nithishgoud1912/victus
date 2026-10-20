"""Release boundaries; source tests alone never qualify the frozen bundle."""

import importlib.util
import json
import sqlite3
import sys
from contextlib import closing
from pathlib import Path
from xml.etree import ElementTree

import pytest

from victus.runtime.instance_lock import InstanceLock
from victus.runtime.paths import dashboard_root
from victus.runtime.release import maintain, prerequisites
from victus.settings import Settings
from victus.storage.migrations import _discover_migrations, current_version, migrate

ROOT = Path(__file__).resolve().parents[2]


def test_frozen_dashboard_paths_use_immutable_bundle(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert dashboard_root() == tmp_path / "dashboard"


def test_normal_user_manifest_and_no_autostart_install():
    tree = ElementTree.parse(ROOT / "packaging/windows/app.manifest")
    level = tree.find(".//{urn:schemas-microsoft-com:asm.v3}requestedExecutionLevel")
    assert level.attrib == {"level": "asInvoker", "uiAccess": "false"}
    spec = (ROOT / "packaging/windows/victus.spec").read_text()
    assert "exclude_binaries=True" in spec and "COLLECT(" in spec and "uac_admin=False" in spec


def test_packaged_worker_entry_runs_freeze_support_first():
    entry = (ROOT / "packaging/windows/entry.py").read_text()
    assert entry.index("multiprocessing.freeze_support()") < entry.index("from victus.cli import main")
    assert '"mcp-note-server"' in entry


def test_default_data_path_is_user_owned_and_does_not_enable_listening(monkeypatch, tmp_path):
    monkeypatch.delenv("VICTUS_DATA_DIR", raising=False)
    monkeypatch.delenv("VICTUS_WAKE_MANIFEST_PATH", raising=False)
    monkeypatch.delenv("VICTUS_VOICE_MODEL_PATH", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    settings = Settings.from_env()
    assert settings.data_dir == tmp_path / "VICTUS"
    assert settings.voice_model_path is None and settings.wake_manifest_path is None
    assert not settings.emergency_hotkey


def test_missing_prerequisite_messages_are_safe_and_explicit(monkeypatch, tmp_path):
    def fail(*a, **kw):
        raise OSError("private endpoint response")

    monkeypatch.setattr("victus.runtime.release.httpx.Client.get", fail)
    monkeypatch.delenv("PLAYWRIGHT_BROWSERS_PATH", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    result = prerequisites(Settings(tmp_path / "data", "x" * 40))
    assert result["ollama"] == "unavailable" and result["browser"] == "not_installed"
    assert result["voice"] == "local_model_not_configured_or_missing"
    assert result["cloud"] == "disabled" and result["wake"] == "off_until_explicitly_enabled"
    assert "private endpoint" not in json.dumps(result)


def test_v6_schema_fixture_migrates_to_current_offline(tmp_path):
    root = tmp_path / "data"
    root.mkdir()
    path = root / "victus.sqlite3"
    with closing(sqlite3.connect(path)) as db:
        db.execute("CREATE TABLE schema_versions(version INTEGER PRIMARY KEY, filename TEXT)")
        for number, sql_path in _discover_migrations():
            if number > 6:
                break
            db.executescript(sql_path.read_text())
            db.execute("INSERT INTO schema_versions VALUES(?,?)", (number, sql_path.name))
            db.commit()
    assert current_version(path) == 6
    result = maintain("migrate", Settings(root, "x" * 40))
    assert result == {"applied": [7, 8], "schema": 8}
    assert maintain("migrate", Settings(root, "x" * 40))["applied"] == []


def test_live_instance_blocks_offline_update_backup_and_migration(tmp_path):
    settings = Settings(tmp_path, "x" * 40)
    migrate(tmp_path / "victus.sqlite3")
    lock = InstanceLock(tmp_path)
    lock.acquire()
    try:
        for command in ("migrate", "backup"):
            with pytest.raises(RuntimeError, match="Another VICTUS"):
                maintain(command, settings, destination=tmp_path.parent / "new-backup")
    finally:
        lock.release()


def test_newer_schema_rejected_before_application_runs(tmp_path):
    path = tmp_path / "victus.sqlite3"
    migrate(path)
    with closing(sqlite3.connect(path)) as db, db:
        db.execute("INSERT INTO schema_versions(version,filename) VALUES(999,'future.sql')")
    with pytest.raises(RuntimeError, match="newer"):
        migrate(path)
    with pytest.raises(ValueError, match="newer"):
        maintain("migrate", Settings(tmp_path, "x" * 40))


def test_release_manifest_excludes_private_payloads(tmp_path):
    spec = importlib.util.spec_from_file_location("release_manifest", ROOT / "packaging/windows/release_manifest.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    (tmp_path / "Victus.exe").write_bytes(b"fixture")
    result = module.create(tmp_path)
    assert result["autostart"] is False and not result["listening_after_install"]
    assert result["files"][0]["path"] == "Victus.exe"
    (tmp_path / "release-manifest.json").unlink()
    (tmp_path / "secret.sqlite3").write_bytes(b"private")
    with pytest.raises(ValueError):
        module.create(tmp_path)
