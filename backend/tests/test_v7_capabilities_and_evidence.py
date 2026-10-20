"""Current read-only readiness and retained partial native evidence, not hardware proof."""

import json

import pytest
from fastapi.testclient import TestClient

from victus.api.app import create_app
from victus.settings import Settings
from victus.workflows import native_qualification as native
from victus.workflows import qualification_records as records

TOKEN = "v7-test-" + "x" * 40
HEADERS = {"Authorization": "Bearer " + TOKEN}
PIN = "a" * 64


@pytest.mark.parametrize("pressure", ["ram", "telemetry", "disk", "disk_unavailable"])
def test_capabilities_sample_current_resources_without_creating_work(
    tmp_path, monkeypatch, isolated_resources, pressure
):
    with TestClient(
        create_app(Settings(tmp_path / "runtime", TOKEN)), base_url="http://127.0.0.1"
    ) as client:
        tasks = client.app.state.services.tasks
        before = tasks.database.list_tasks()
        if pressure == "ram":
            isolated_resources.probe = lambda: {"available_bytes": 1}
            expected = "LOCAL_RESOURCE_PRESSURE"
        elif pressure == "telemetry":
            isolated_resources.probe = lambda: {}
            expected = "LOCAL_RESOURCE_TELEMETRY_UNAVAILABLE"
        else:
            from victus.runtime.resources import ResourcePressure

            expected = "LOCAL_DISK_PRESSURE" if pressure == "disk" else "LOCAL_DISK_UNAVAILABLE"

            def disk(_):
                raise ResourcePressure(expected)

            monkeypatch.setattr(isolated_resources, "check_disk", disk)
        response = client.get("/api/workflows/capabilities", headers=HEADERS)
        assert response.status_code == 200
        result = response.json()
        assert result["resource_blocked"] and result["resource_reason"] == expected
        assert not result["notepad_checklist"]["enabled"]
        assert not result["browser_research"]["enabled"]
        assert tasks.database.list_tasks() == before


def test_current_readiness_recovers_from_stale_pressure_cache(tmp_path, isolated_resources):
    with TestClient(
        create_app(Settings(tmp_path / "runtime", TOKEN)), base_url="http://127.0.0.1"
    ) as client:
        with isolated_resources._lock:
            isolated_resources._sample["available_bytes"] = 1
        response = client.get("/api/workflows/capabilities", headers=HEADERS).json()
        assert response["resource_blocked"] is False and response["resource_reason"] is None


@pytest.fixture
def native_session(tmp_path, monkeypatch):
    from test_v4_portable_qualification import native_report, runs_report, write

    monkeypatch.setattr(native, "runtime_identity", lambda: PIN)
    monkeypatch.setattr(records, "runtime_identity", lambda: PIN)
    monkeypatch.setattr(native, "_native_profile", lambda _: None)
    monkeypatch.setattr(records, "_native_profile", lambda _: None)
    monkeypatch.setenv("VICTUS_QUALIFICATION_DIR", str(tmp_path / "admission"))
    report = native_report(tmp_path)
    identity = {
        key: report[key]
        for key in ("profile", "runtime_sha256", "profiles_sha256", "executable_sha256")
    }
    write(tmp_path / "session.json", {"kind": "native_session", **identity})
    batch = tmp_path / "runs" / "batch"
    run = runs_report(batch, ".txt")
    run.update(
        **identity,
        kind="notepad",
        status="succeeded",
        native_windows=True,
    )
    write(batch / "notepad-qualification.json", run)
    for index, dpi in enumerate((96, 120), 1):
        (tmp_path / f"dpi-{index}.json").write_bytes((tmp_path / f"dpi-{dpi}.json").read_bytes())
    return tmp_path


@pytest.mark.parametrize(
    "case",
    [
        "case_missing",
        "case_truncated",
        "case_shape",
        "evidence_changed",
        "dpi_missing",
        "dpi_truncated",
        "run_missing",
        "run_truncated",
        "run_shape",
        "run_items",
    ],
)
def test_incomplete_native_inputs_retain_aggregate_and_cannot_promote(native_session, case):
    root = native_session
    name = sorted(records.NATIVE_CHECKS)[0]
    target = root / "cases" / (name + ".json")
    if case.startswith("dpi_"):
        target = root / "dpi-1.json"
    elif case.startswith("run_"):
        target = root / "runs/batch/notepad-qualification.json"
    elif case == "evidence_changed":
        target = root / "evidence" / (name + ".json")
    if case.endswith("missing"):
        target.unlink()
    elif case.endswith("shape"):
        target.write_text("[]")
    elif case == "run_items":
        value = json.loads(target.read_text())
        value["runs"] = [None]
        target.write_text(json.dumps(value))
    else:
        target.write_text("{")
    output = root / "assembled.json"
    assert native.assemble_session(root / "session.json", output) == output
    result = json.loads(output.read_text())
    assert result["qualified"] is False and result["passed"] is False and result["missing"]
    assert str(root) not in json.dumps(result)
    with pytest.raises(ValueError):
        records.promote_native(output)
    assert not records.qualification_path("native").exists()


def test_complete_synthetic_native_assembly_still_promotes_exclusively(native_session):
    root = native_session
    output = native.assemble_session(root / "session.json", root / "assembled.json")
    report = json.loads(output.read_text())
    assert report["qualified"] and report["verified_runs"] == 20
    assert report["missing"] == []
    installed = records.promote_native(output)
    assert installed.is_file()
    with pytest.raises(FileExistsError):
        records.promote_native(output)


def test_invalid_prepared_session_or_outside_output_is_still_refused(native_session):
    root = native_session
    with pytest.raises(ValueError):
        native.assemble_session(root / "session.json", root.parent / "outside.json")
    value = json.loads((root / "session.json").read_text())
    value["runtime_sha256"] = "b" * 64
    (root / "session.json").write_text(json.dumps(value))
    with pytest.raises(ValueError):
        native.assemble_session(root / "session.json", root / "assembled.json")
    assert not (root / "assembled.json").exists()
