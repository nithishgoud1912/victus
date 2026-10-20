"""Supplementary intake contracts never stand in for inference evidence."""

import json
from pathlib import Path

import pytest

from victus.agent.intake_evaluation import evaluate

SUITE = Path(__file__).resolve().parents[2] / "evaluation/v8-command-intake-v1.json"


def test_frozen_intake_contract_has_no_effects(tmp_path):
    before = SUITE.read_bytes()
    report = evaluate(SUITE, tmp_path / "report.json")
    assert report["total"] == report["passed"] == 20
    assert report["status"] == "passed"
    assert not report["model_inference"]
    assert not report["tool_execution"]
    assert not report["model_qualified"]
    assert not report["original_30_goal_gate_replaced"]
    assert SUITE.read_bytes() == before
    assert [p.name for p in tmp_path.iterdir()] == ["report.json"]
    with pytest.raises(FileExistsError):
        evaluate(SUITE, tmp_path / "report.json")


def test_failed_expectation_retained(tmp_path):
    suite = json.loads(SUITE.read_text())
    suite["cases"] = [suite["cases"][0]]
    suite["cases"][0]["expected"] = {"rejected": True}
    source = tmp_path / "suite.json"
    source.write_text(json.dumps(suite))
    report = evaluate(source, tmp_path / "report.json")
    assert report["status"] == "failed"
    assert report["passed"] == 0


def test_duplicate_case_ids_rejected(tmp_path):
    suite = json.loads(SUITE.read_text())
    suite["cases"].append(suite["cases"][0])
    source = tmp_path / "suite.json"
    source.write_text(json.dumps(suite))
    with pytest.raises(ValueError, match="distinct"):
        evaluate(source, tmp_path / "report.json")
    assert not (tmp_path / "report.json").exists()
