"""Phase evidence remains bounded, private and observational."""

import asyncio
import json
from types import SimpleNamespace

import pytest

from victus.adapters.uia.applications import UIABlocked
from victus.workflows.diagnostics import PhaseDiagnostics


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_diagnostics_keep_last_entered_phase_and_suppress_private_error(tmp_path):
    path = tmp_path / "phases.jsonl"
    evidence = PhaseDiagnostics(path, "a" * 32)

    def fail(*_):
        assert rows(path)[-1]["state"] == "started"  # Flushed before adapter entry.
        raise RuntimeError("private text and C:/private/user/file.txt")

    with pytest.raises(RuntimeError):
        evidence.wrap("save.filename_write", fail)()
    evidence.close()
    records = rows(path)
    assert records[-1]["error_code"] == "PHASE_FAILED"
    assert "private" not in path.read_text()
    assert records[-1]["elapsed_ms"] >= 0


def test_diagnostics_preserve_safe_ownership_block_code(tmp_path):
    path = tmp_path / "phases.jsonl"
    evidence = PhaseDiagnostics(path, "b" * 32)
    with pytest.raises(UIABlocked):
        with evidence.phase("uia.launch_profile.execute"):
            raise UIABlocked("OWNED_CHILD_UNAVAILABLE")
    evidence.close()
    assert rows(path)[-1]["error_code"] == "OWNED_CHILD_UNAVAILABLE"


def test_diagnostics_cap_records_filter_metadata_and_refuse_overwrite(tmp_path):
    path = tmp_path / "phases.jsonl"
    evidence = PhaseDiagnostics(path, "c" * 32, limit=3)
    for _ in range(9):
        evidence.record(
            "save.invoke",
            "started",
            metadata={
                "app_ref": "d" * 32,
                "control_ref": "private text",
                "text": "SECRET",
                "owned_pid": 123,
                "process_created": 456,
                "window_dpi": 120,
            },
        )
    evidence.close()
    assert len(rows(path)) == 3
    assert rows(path)[-1]["app_ref"] == "d" * 32
    assert rows(path)[-1]["window_dpi"] == 120
    assert "SECRET" not in path.read_text() and "private" not in path.read_text()
    with pytest.raises(FileExistsError):
        PhaseDiagnostics(path, "e" * 32)


def test_async_verifier_false_and_cancellation_are_not_success(tmp_path):
    path = tmp_path / "phases.jsonl"
    evidence = PhaseDiagnostics(path, "f" * 32)

    async def verify(*_):
        return False

    assert (
        asyncio.run(
            evidence.wrap("uia.save_checklist.verify", verify)(
                {}, SimpleNamespace(app_ref="a" * 32)
            )
        )
        is False
    )

    async def cancelled():
        raise asyncio.CancelledError

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(evidence.wrap("save.cancelled", cancelled)())
    evidence.close()
    assert any(row["state"] == "unverified" for row in rows(path))
    assert rows(path)[-1]["state"] == "error"


def test_diagnostics_do_not_emit_returned_payloads(tmp_path):
    path = tmp_path / "phases.jsonl"
    evidence = PhaseDiagnostics(path, "a" * 32)
    result = {"app_ref": "b" * 32, "filename": "SECRET", "text": "SECRET"}
    assert evidence.wrap("uia.launch_profile.execute", lambda: result)() is result
    evidence.close()
    assert any(row.get("app_ref") == "b" * 32 for row in rows(path))
    assert "SECRET" not in path.read_text()


def test_native_qualification_stops_after_first_uncertain_effect(tmp_path, monkeypatch):
    from victus.tools.dispatcher import DispatchOutcome
    from victus.workflows import qualification

    calls = []

    def uncertain(workspace, kind, request):
        calls.append(request.task_id)
        return DispatchOutcome("unknown", error_code="WORKER_ERROR")

    monkeypatch.setattr(qualification, "os", SimpleNamespace(name="nt"))
    monkeypatch.setattr(qualification, "supervised_run", uncertain)
    path = qualification.qualify(
        "notepad",
        tmp_path / "runtime",
        repetitions=20,
        profiles_file=tmp_path / "reviewed.json",
        profile="candidate",
    )
    report = json.loads(path.read_text())
    assert report["requested"] == 20 and report["executed"] == 1
    assert report["passed"] == 0 and report["status"] == "failed"
    assert report["stopped_after_failed_native_run"]
    assert len(calls) == 1
    # Refuse a prior root before making another native call.
    with pytest.raises(FileExistsError):
        qualification.qualify("notepad", tmp_path / "runtime", profiles_file=tmp_path / "x")
    assert len(calls) == 1
