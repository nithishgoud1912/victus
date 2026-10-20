"""Synthetic bundle boundaries; no Windows executable is run or qualified."""

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from victus.runtime.bundle import verify_bundle
from victus.runtime.source_inventory import verify_source_inventory

ROOT = Path(__file__).resolve().parents[2]


def write(path, value):
    path.write_text(json.dumps(value))


@pytest.fixture
def bundle(tmp_path):
    (tmp_path / "Victus.exe").write_bytes(b"synthetic executable")
    data = (tmp_path / "Victus.exe").read_bytes()
    write(
        tmp_path / "release-manifest.json",
        {
            "format": 1,
            "bundle": "windows-x64-onedir",
            "source_sha256": "a" * 64,
            "files": [
                {
                    "path": "Victus.exe",
                    "bytes": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
            ],
        },
    )
    return tmp_path


def test_exact_bundle_checks_do_not_qualify_release(bundle):
    report = verify_bundle(bundle)
    assert report["integrity_verified"] and not report["release_qualified"]
    assert report["files_verified"] == 1


@pytest.mark.parametrize(
    "change", ["extra", "changed", "missing", "duplicate", "escape", "source", "link"]
)
def test_bundle_changes_refused(bundle, change):
    manifest = bundle / "release-manifest.json"
    value = json.loads(manifest.read_text())
    if change == "extra":
        (bundle / "unlisted.dll").write_bytes(b"unexpected")
    elif change == "changed":
        (bundle / "Victus.exe").write_bytes(b"changed bytes")
    elif change == "missing":
        (bundle / "Victus.exe").unlink()
    elif change == "duplicate":
        value["files"].append(value["files"][0])
    elif change == "escape":
        value["files"][0]["path"] = "../escape"
    elif change == "source":
        value.pop("source_sha256")
    else:
        (bundle / "linked").symlink_to(bundle / "Victus.exe")
    write(manifest, value)
    with pytest.raises((ValueError, OSError)):
        verify_bundle(bundle)


def test_manifest_publication_preserves_existing_bytes(tmp_path, monkeypatch):
    monkeypatch.delenv("VICTUS_BUILD_SOURCE_MANIFEST", raising=False)
    spec = importlib.util.spec_from_file_location(
        "release_manifest_v9", ROOT / "packaging/windows/release_manifest.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    (tmp_path / "Victus.exe").write_bytes(b"fixture")
    module.create(tmp_path)
    original = (tmp_path / "release-manifest.json").read_bytes()
    with pytest.raises(FileExistsError):
        module.create(tmp_path)
    assert (tmp_path / "release-manifest.json").read_bytes() == original


def test_source_identity_detects_bytes_and_digest_drift(tmp_path):
    source = tmp_path / "input.py"
    source.write_bytes(b"fixture")
    entries = {"input.py": {"bytes": 7, "sha256": hashlib.sha256(b"fixture").hexdigest()}}
    digest = hashlib.sha256(
        json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    manifest = tmp_path / "source.json"
    write(manifest, {"files": entries, "source_sha256": digest})
    assert verify_source_inventory(manifest, tmp_path) == digest
    source.write_bytes(b"changed")
    with pytest.raises(ValueError, match="changed"):
        verify_source_inventory(manifest, tmp_path)
    source.write_bytes(b"fixture")
    write(manifest, {"files": entries, "source_sha256": "b" * 64})
    with pytest.raises(ValueError, match="digest"):
        verify_source_inventory(manifest, tmp_path)


@pytest.mark.parametrize(
    "name", ["model.bin", "secret.db", "recording.mp3", "model.gguf", "data.sqlite3-wal"]
)
def test_manifest_refuses_external_models_and_private_runtime_files(tmp_path, monkeypatch, name):
    monkeypatch.delenv("VICTUS_BUILD_SOURCE_MANIFEST", raising=False)
    spec = importlib.util.spec_from_file_location(
        "manifest_assets", ROOT / "packaging/windows/release_manifest.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    (tmp_path / "Victus.exe").write_bytes(b"fixture")
    (tmp_path / name).write_bytes(b"private fixture")
    with pytest.raises(ValueError, match="private or large external asset"):
        module.create(tmp_path)
    assert not (tmp_path / "release-manifest.json").exists()


def test_verify_bundle_cli_is_read_only(bundle, monkeypatch, capsys):
    from victus.cli import main

    monkeypatch.setattr("sys.argv", ["victus", "verify-bundle", "--source", str(bundle)])
    main()
    assert json.loads(capsys.readouterr().out)["integrity_verified"]
    assert {path.name for path in bundle.iterdir()} == {"Victus.exe", "release-manifest.json"}


def test_frozen_service_rejects_bad_inventory_before_settings(monkeypatch):
    from victus.cli import main

    def reject(_):
        raise ValueError("changed fixture")

    def settings_forbidden():
        pytest.fail("Settings/data initialization must not precede frozen integrity check")

    monkeypatch.setattr("sys.argv", ["Victus.exe", "serve"])
    monkeypatch.setattr("sys.frozen", True, raising=False)
    monkeypatch.setattr("victus.runtime.bundle.verify_bundle", reject)
    monkeypatch.setattr("victus.cli.Settings.from_env", settings_forbidden)
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 2


def test_complete_source_requirement_rejects_subset(tmp_path, monkeypatch):
    data = b"fixture"
    (tmp_path / "input.py").write_bytes(data)
    entries = {"input.py": {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}}
    digest = hashlib.sha256(
        json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    manifest = tmp_path / "source.json"
    write(manifest, {"files": entries, "source_sha256": digest})
    monkeypatch.setattr(
        "victus.runtime.source_inventory.capture_entries",
        lambda _: {**entries, "other.py": entries["input.py"]},
    )
    with pytest.raises(ValueError, match="omits or adds"):
        verify_source_inventory(manifest, tmp_path, require_complete=True)
