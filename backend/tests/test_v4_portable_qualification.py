"""Portable V4 evidence tests. Synthetic files/receipts never qualify devices."""

import hashlib
import importlib.metadata
import json
import sqlite3
import sys
import types
from contextlib import closing
from unittest.mock import Mock

import pytest

from victus.workflows import qualification_records as records

PIN = "a" * 64


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


@pytest.fixture
def fixed_runtime(monkeypatch, tmp_path):
    monkeypatch.setattr(records, "runtime_identity", lambda: PIN)
    monkeypatch.setenv("VICTUS_QUALIFICATION_DIR", str(tmp_path / "admission"))


@pytest.mark.parametrize("raw", ["[]", '{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}'])
def test_strict_evidence_json_rejects_invalid_shapes(tmp_path, raw):
    path = tmp_path / "record.json"
    path.write_text(raw)
    with pytest.raises(ValueError):
        records.read_record(path)


def test_evidence_size_bound_precedes_hashing(tmp_path, monkeypatch):
    path = tmp_path / "record.json"
    path.write_text("{}" * 10)
    hash_call = Mock(side_effect=AssertionError("Oversized file must not be hashed"))
    monkeypatch.setattr(records, "file_hash", hash_call)
    with pytest.raises(ValueError, match="bound"):
        records.read_record(path, maximum=4)
    hash_call.assert_not_called()


def test_linked_evidence_and_ancestor_rejected(tmp_path):
    actual = tmp_path / "actual"
    actual.mkdir()
    path = write(actual / "record.json", {})
    link = tmp_path / "alias"
    link.symlink_to(actual, target_is_directory=True)
    with pytest.raises(ValueError, match="Linked"):
        records.read_record(link / path.name)


def runs_report(root, suffix=".json"):
    (root / "workspace").mkdir(parents=True)
    db = root / "victus.sqlite3"
    with closing(sqlite3.connect(db)) as connection:
        connection.execute(
            "CREATE TABLE action_attempts(action_id TEXT PRIMARY KEY, status TEXT, sha256 TEXT, expected_effect_ref TEXT)"
        )
        runs = []
        for index in range(20):
            name = f"artifact-{index:02}{suffix}"
            if suffix == ".json":
                artifact = {
                    "kind": "browser_research",
                    "status": "succeeded",
                    "required_sources": 2,
                    "observed_count": 2,
                    "sources": [
                        {
                            "url": f"http://127.0.0.1:12345/source-{letter}.html",
                            "text": letter,
                            "text_sha256": hashlib.sha256(letter.encode()).hexdigest(),
                            "observation_id": f"observation-{letter}",
                        }
                        for letter in ("a", "b")
                    ],
                }
                write(root / "workspace" / name, artifact)
            else:
                (root / "workspace" / name).write_text("synthetic native test artifact")
            digest = records.file_hash(root / "workspace" / name)
            task, action = f"task-{index}", f"{index:032x}"
            connection.execute(
                "INSERT INTO action_attempts VALUES(?,?,?,?)",
                (action, "verified", digest, "task:" + task),
            )
            runs.append(
                {
                    "destination": name,
                    "verified": True,
                    "sha256": digest,
                    "task_id": task,
                    "action_id": action,
                    "owned_cleanup": True,
                    "replay": True,
                    "route": "structured" if index % 2 == 0 else "text",
                }
            )
        connection.commit()
    return {
        "schema_version": 2,
        "runtime_sha256": PIN,
        "runtime_end_sha256": PIN,
        "qualified": True,
        "passed": True,
        "normal_memory_guards": True,
        "verified_runs": 20,
        "runs": runs,
    }


@pytest.mark.usefixtures("fixed_runtime")
def test_valid_artifacts_require_matching_readonly_ledger(tmp_path):
    report = runs_report(tmp_path)
    assert records._validate_runs(report, tmp_path / "report.json", ".json") == report["runs"]
    with closing(sqlite3.connect(tmp_path / "victus.sqlite3")) as connection:
        connection.execute(
            "UPDATE action_attempts SET status='unknown' WHERE action_id=?",
            (report["runs"][0]["action_id"],),
        )
        connection.commit()
    with pytest.raises(ValueError, match="receipt"):
        records._validate_runs(report, tmp_path / "report.json", ".json")


@pytest.mark.parametrize(
    "case",
    [
        "short",
        "duplicate_file",
        "duplicate_task",
        "wrong_hash",
        "escape",
        "bool_count",
        "missing_artifact",
    ],
)
@pytest.mark.usefixtures("fixed_runtime")
def test_incomplete_or_changed_runs_never_promote(tmp_path, case):
    report = runs_report(tmp_path)
    if case == "short":
        report["runs"].pop()
        report["verified_runs"] = 19
    elif case == "duplicate_file":
        report["runs"][1]["destination"] = report["runs"][0]["destination"]
    elif case == "duplicate_task":
        report["runs"][1]["task_id"] = report["runs"][0]["task_id"]
    elif case == "wrong_hash":
        report["runs"][0]["sha256"] = "b" * 64
    elif case == "escape":
        report["runs"][0]["run_root"] = "../outside"
    elif case == "bool_count":
        report["verified_runs"] = True
    else:
        (tmp_path / "workspace" / report["runs"][0]["destination"]).unlink()
    with pytest.raises((ValueError, OSError)):
        records._validate_runs(report, tmp_path / "report.json", ".json")


def fixture_report(root, monkeypatch):
    from victus.workflows.fixture_research import FIXTURE_HASH

    report = runs_report(root)
    executable = root / "engine" / "bin" / "chrome.exe"
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b"synthetic binary")
    fake = Mock()
    fake.__enter__ = Mock(
        return_value=types.SimpleNamespace(
            chromium=types.SimpleNamespace(executable_path=str(executable))
        )
    )
    fake.__exit__ = Mock(return_value=False)
    monkeypatch.setattr("playwright.sync_api.sync_playwright", lambda: fake)
    report.update(
        kind="fixture",
        checks=dict.fromkeys(records.BROWSER_CHECKS, True),
        fixture_sha256=FIXTURE_HASH,
        playwright_version=importlib.metadata.version("playwright"),
        browser_sha256=records.file_hash(executable),
        browser_relative_path="/".join(executable.parts[-3:]),
    )
    return report


@pytest.mark.usefixtures("fixed_runtime")
def test_complete_fixture_promotion_is_exclusive(tmp_path, monkeypatch):
    report = fixture_report(tmp_path, monkeypatch)
    path = write(tmp_path / "report.json", report)
    destination = records.promote_fixture(path)
    assert records.qualified_record(destination, "fixture", records.BROWSER_CHECKS)
    with pytest.raises(FileExistsError):
        records.promote_fixture(path)


@pytest.mark.parametrize(
    "change", ["routes", "source_hash", "alias", "browser_hash", "stale_runtime", "guard"]
)
@pytest.mark.usefixtures("fixed_runtime")
def test_fixture_promotion_rejects_missing_actual_evidence(tmp_path, monkeypatch, change):
    report = fixture_report(tmp_path, monkeypatch)
    if change == "routes":
        for run in report["runs"]:
            run["route"] = "structured"
    elif change in {"source_hash", "alias"}:
        run = report["runs"][0]
        path = tmp_path / "workspace" / run["destination"]
        artifact = json.loads(path.read_text())
        if change == "source_hash":
            artifact["sources"][0]["text_sha256"] = "b" * 64
        else:
            artifact["sources"][1]["url"] = artifact["sources"][0]["url"]
        write(path, artifact)
        run["sha256"] = records.file_hash(path)
        with closing(sqlite3.connect(tmp_path / "victus.sqlite3")) as connection:
            connection.execute(
                "UPDATE action_attempts SET sha256=? WHERE action_id=?",
                (run["sha256"], run["action_id"]),
            )
            connection.commit()
    elif change == "browser_hash":
        report["browser_sha256"] = "b" * 64
    elif change == "stale_runtime":
        report["runtime_end_sha256"] = "b" * 64
    else:
        report["normal_memory_guards"] = False
    with pytest.raises(ValueError):
        records.promote_fixture(write(tmp_path / "report.json", report))
    assert not records.qualification_path("fixture").exists()


def test_external_qualification_root_requires_absolute_path(monkeypatch):
    monkeypatch.setenv("VICTUS_QUALIFICATION_DIR", "relative")
    with pytest.raises(ValueError, match="absolute"):
        records.qualification_path("native")


def test_frozen_identity_verifies_bundle_and_invalidates_modified_files(tmp_path, monkeypatch):
    executable = tmp_path / "Victus.exe"
    executable.write_bytes(b"synthetic executable")
    manifest = {
        "source_sha256": "a" * 64,
        "files": [
            {
                "path": executable.name,
                "bytes": executable.stat().st_size,
                "sha256": records.file_hash(executable),
            }
        ],
    }
    write(tmp_path / "release-manifest.json", manifest)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(executable))
    monkeypatch.setattr(records, "_FROZEN_CACHE", None)
    before = records.runtime_identity()
    assert records.runtime_identity() == before
    manifest["source_sha256"] = "b" * 64
    write(tmp_path / "release-manifest.json", manifest)
    assert records.runtime_identity() != before
    executable.write_bytes(b"corrupted executable")
    with pytest.raises(ValueError, match="changed"):
        records.runtime_identity()


@pytest.mark.parametrize(
    "name", ["../escape.exe", "/escape.exe", "C:escape.exe", "folder\\escape.exe", ""]
)
def test_frozen_inventory_rejects_unsafe_paths(tmp_path, name):
    with pytest.raises(ValueError):
        records._verify_frozen_files(
            tmp_path, {"files": [{"path": name, "bytes": 1, "sha256": PIN}]}, PIN
        )


def native_report(root):
    report = runs_report(root, ".txt")
    report.update(
        kind="native",
        profile="synthetic-profile",
        profiles_sha256="b" * 64,
        executable_sha256="c" * 64,
        physical_dpi=[96, 120],
        checks=dict.fromkeys(records.NATIVE_CHECKS, True),
        case_reports={},
        dpi_reports=[],
    )
    identity = {
        key: report[key]
        for key in (
            "profile",
            "profiles_sha256",
            "executable_sha256",
            "runtime_sha256",
            "runtime_end_sha256",
        )
    }
    for name in records.NATIVE_CHECKS:
        evidence = write(root / "evidence" / (name + ".json"), {"synthetic": True})
        case = write(
            root / "cases" / (name + ".json"),
            {
                "schema_version": 2,
                **identity,
                "check": name,
                "passed": True,
                "real_windows": True,
                "normal_memory_guards": True,
                "evidence": [
                    {
                        "file": evidence.relative_to(root).as_posix(),
                        "sha256": records.file_hash(evidence),
                    }
                ],
            },
        )
        report["case_reports"][name] = {
            "file": case.relative_to(root).as_posix(),
            "sha256": records.file_hash(case),
        }
    for dpi in (96, 120):
        case = write(
            root / f"dpi-{dpi}.json",
            {
                "schema_version": 2,
                **identity,
                "dpi": dpi,
                "passed": True,
                "real_windows": True,
                "physical_observed": True,
            },
        )
        report["dpi_reports"].append({"file": case.name, "sha256": records.file_hash(case)})
    return report


@pytest.mark.usefixtures("fixed_runtime")
def test_complete_native_report_can_be_promoted_without_executing_native_code(
    tmp_path, monkeypatch
):
    report = native_report(tmp_path)
    sentinel = records.NativeAdmission(tmp_path / "profile.json", frozenset({report["profile"]}))
    monkeypatch.setattr(records, "_native_profile", lambda _: sentinel)
    records.promote_native(write(tmp_path / "report.json", report))
    assert records.qualified_native() == sentinel


@pytest.mark.parametrize(
    "change",
    [
        "pending_case",
        "tampered_case",
        "tampered_backing_evidence",
        "one_dpi",
        "changed_dpi_identity",
    ],
)
@pytest.mark.usefixtures("fixed_runtime")
def test_native_missing_or_changed_observations_do_not_grant_authority(
    tmp_path, monkeypatch, change
):
    report = native_report(tmp_path)
    monkeypatch.setattr(records, "_native_profile", lambda _: None)
    name = sorted(records.NATIVE_CHECKS)[0]
    if change == "pending_case":
        report["checks"][name] = False
    elif change == "tampered_case":
        (tmp_path / report["case_reports"][name]["file"]).write_text("{}")
    elif change == "tampered_backing_evidence":
        (tmp_path / "evidence" / (name + ".json")).write_text("{}")
    elif change == "one_dpi":
        report["physical_dpi"] = [96, 96]
    else:
        path = tmp_path / report["dpi_reports"][0]["file"]
        value = json.loads(path.read_text())
        value["runtime_end_sha256"] = "d" * 64
        write(path, value)
        report["dpi_reports"][0]["sha256"] = records.file_hash(path)
    with pytest.raises(ValueError):
        records.promote_native(write(tmp_path / "report.json", report))
    assert not records.qualification_path("native").exists()


@pytest.mark.usefixtures("fixed_runtime")
def test_partial_native_assembly_preserves_incomplete_report(tmp_path, monkeypatch):
    from victus.workflows import native_qualification as native

    monkeypatch.setattr(native, "runtime_identity", lambda: PIN)
    monkeypatch.setattr(native, "_native_profile", lambda _: None)
    identity = {
        "profile": "synthetic",
        "runtime_sha256": PIN,
        "profiles_sha256": "b" * 64,
        "executable_sha256": "c" * 64,
    }
    session = write(tmp_path / "session.json", {"kind": "native_session", **identity})
    (tmp_path / "runs").mkdir()
    for name in records.NATIVE_CHECKS:
        write(
            tmp_path / "cases" / (name + ".json"),
            {"schema_version": 2, **identity, "check": name, "passed": False, "evidence": []},
        )
    for index in (1, 2):
        write(tmp_path / f"dpi-{index}.json", {"passed": False, "dpi": None})
    output = native.assemble_session(session, tmp_path / "report.json")
    report = json.loads(output.read_text())
    assert report["qualified"] is False and report["passed"] is False
    assert set(records.NATIVE_CHECKS) <= set(report["missing"])


def test_missing_browser_startup_still_writes_failure_report(tmp_path, monkeypatch):
    from victus.workflows import fixture_qualification as runner

    monkeypatch.setattr(runner, "runtime_identity", lambda: PIN)
    monkeypatch.setattr(runner, "system_memory", lambda: {"available_bytes": 8 * 1024**3})
    fake = Mock()
    fake.__enter__ = Mock(
        return_value=types.SimpleNamespace(
            chromium=types.SimpleNamespace(executable_path=str(tmp_path / "missing.exe"))
        )
    )
    fake.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(runner, "sync_playwright", lambda: fake)
    out = tmp_path / "attempt"
    assert runner.main(["--output", str(out), "--repetitions", "1"]) == 2
    report = json.loads((out / "report.json").read_text())
    assert report["qualified"] is False and report["passed"] is False
    assert report["failure"] and report["boundary"] == "startup"
    assert report["browser_sha256"] is None
    assert report["verified_runs"] == 0


def test_native_profile_admission_binds_config_and_executable_bytes(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    workflow = root / "backend" / "victus" / "workflows" / "qualification_records.py"
    monkeypatch.setattr(records, "__file__", str(workflow))
    executable = tmp_path / "candidate.exe"
    executable.write_bytes(b"synthetic executable")
    profile = write(
        root / "config/applications/candidate.json",
        [
            {
                "name": "candidate",
                "executable": str(executable),
                "executable_sha256": records.file_hash(executable),
                "launch_mode": "owned_child",
                "window": {"control_type": "Window", "automation_id": "main"},
                "controls": {"editor": {"control_type": "Edit", "automation_id": "editor"}},
            }
        ],
    )
    proof = {
        "profile": "candidate",
        "profiles_sha256": records.file_hash(profile),
        "executable_sha256": records.file_hash(executable),
    }
    assert records._native_profile(proof).profiles == frozenset({"candidate"})
    executable.write_bytes(b"changed executable")
    with pytest.raises(ValueError, match="changed"):
        records._native_profile(proof)
