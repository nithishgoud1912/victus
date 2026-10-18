"""Historical evidence is allowlisted, hash-bound, and never inferred from progress."""

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/reconcile-v36-evidence.py"
spec = importlib.util.spec_from_file_location("reconcile_v36", SCRIPT)
evidence = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evidence)


def write(root, name, data):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_missing_reports_are_unknown_and_progress_cannot_qualify(tmp_path):
    write(
        tmp_path,
        ".local/v36-soak-standard-04/progress.json",
        {"qualified": True, "tasks_verified": 900, "private": "SECRET"},
    )
    report = evidence.reconcile(tmp_path)
    assert not report["soak"]["qualified"]
    assert not report["soak"]["final_report_available"]
    assert report["package_self_test"] is None
    assert report["historical_junit"] is None
    assert report["soak"]["tasks_verified"] == 900
    assert "SECRET" not in json.dumps(report)
    assert not report["release_qualified"]


def test_inventory_digest_and_literal_boolean_checks():
    entries = {"backend/victus/example.py": {"sha256": "a" * 64, "bytes": 10}}
    digest = hashlib.sha256(
        json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    assert evidence.manifest_identity({"files": entries, "source_sha256": digest}) == digest
    with pytest.raises(ValueError, match="digest mismatch"):
        evidence.manifest_identity({"files": entries, "source_sha256": "b" * 64})
    assert not evidence.passing_checks({"checks": {"forged": 1}})["all_recorded_checks_true"]


def test_report_hash_is_from_exact_bytes_not_reconstructed_json(tmp_path):
    path = tmp_path / "report.json"
    path.write_bytes(b'{ "passed": true, "private": "SECRET" }\n')
    references = {}
    record = evidence.read_record(tmp_path, "report.json", references)
    assert record["passed"] is True
    assert references["report.json"]["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert "SECRET" not in json.dumps(references)
