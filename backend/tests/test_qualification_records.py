"""Trusted admission refuses partial/stale records and never accepts client authority."""

import json

import pytest

from victus.workflows import qualification_records as records


def proof():
    return {"schema_version": 2, "kind": "fixture", "qualified": True,
            "runtime_sha256": records.runtime_identity(), "verified_runs": 20,
            "report_sha256": "a" * 64,
            "checks": dict.fromkeys(records.BROWSER_CHECKS, True)}


@pytest.mark.parametrize("change", [{"qualified": 1}, {"verified_runs": True},
    {"verified_runs": 19}, {"runtime_sha256": "b" * 64}, {"checks": {}},
    {"report_sha256": "invalid"}, {"kind": "public"}])
def test_partial_or_stale_proofs_never_admit(tmp_path, change):
    path = tmp_path / "proof.json"
    path.write_text(json.dumps({**proof(), **change}))
    assert records.qualified_record(path, "fixture", records.BROWSER_CHECKS) is None


def test_matching_proof_and_missing_or_invalid_record(tmp_path):
    path = tmp_path / "proof.json"
    assert records.qualified_record(path, "fixture", records.BROWSER_CHECKS) is None
    path.write_text("{")
    assert records.qualified_record(path, "fixture", records.BROWSER_CHECKS) is None
    value = proof()
    path.write_text(json.dumps(value))
    assert records.qualified_record(path, "fixture", records.BROWSER_CHECKS) == value
    value["checks"]["owned_cleanup"] = 1
    path.write_text(json.dumps(value))
    assert records.qualified_record(path, "fixture", records.BROWSER_CHECKS) is None


def test_runtime_binding_changes_with_runtime_bytes_not_qualification_data(tmp_path, monkeypatch):
    root = tmp_path / "victus"
    workflow = root / "workflows"
    workflow.mkdir(parents=True)
    runtime = workflow / "qualification_records.py"
    runtime.write_text("first version")
    monkeypatch.setattr(records, "__file__", str(runtime))
    before = records.runtime_identity()
    (workflow / "fixture-qualification.json").write_text("{}")
    assert records.runtime_identity() == before
    runtime.write_text("changed implementation")
    assert records.runtime_identity() != before


def test_promotion_rejects_claimed_success_without_twenty_verified_artifacts(tmp_path):
    path = tmp_path / "report.json"
    path.write_text(json.dumps({**proof(), "passed": True, "runs": [],
                               "normal_memory_guards": True}))
    with pytest.raises(ValueError):
        records.promote_fixture(path)


def test_native_missing_record_never_registers_a_profile():
    assert records.qualified_native() is None
