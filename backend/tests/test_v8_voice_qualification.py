"""Synthetic evidence/asset boundaries only; no acoustic or device qualification."""

import json

import pytest
from test_v4_voice_and_readiness import reports, write

from victus.voice import qualification_session as voice
from victus.voice.model_assets import model_identity

pytest_plugins = ["test_v4_voice_and_readiness"]


@pytest.mark.parametrize(
    "change",
    [
        "negative_wer",
        "inflated_intent",
        "inflated_target",
        "negative_action",
        "float_count",
        "bool_count",
        "groups_list",
        "physical_list",
        "missing_corrections",
        "wrong_correction_rate",
        "different_stt",
        "missing_stt",
        "physical_asset_drift",
    ],
)
def test_invalid_metrics_assets_and_correction_evidence_cannot_qualify(session, change):
    recognition, actions, physical = reports(session)
    if change == "negative_wer":
        recognition["groups"]["quiet"]["word_error_rate"] = -1
    elif change == "inflated_intent":
        recognition["groups"]["quiet"]["intent_accuracy"] = 2
    elif change == "inflated_target":
        recognition["groups"]["quiet"]["target_accuracy"] = 2
    elif change == "negative_action":
        actions["groups"]["quiet"]["accuracy"] = -0.1
    elif change in {"float_count", "bool_count"}:
        recognition["groups"]["quiet"]["samples"] = 50.0 if change == "float_count" else True
    elif change == "groups_list":
        recognition["groups"] = []
    elif change == "physical_list":
        physical["checks"] = []
    elif change == "missing_corrections":
        del actions["groups"]["quiet"]["corrections_measured"]
    elif change == "wrong_correction_rate":
        actions["groups"]["quiet"]["correction_rate"] = 0.99
    elif change == "different_stt":
        recognition["stt_model_sha256"] = "b" * 64
    elif change == "missing_stt":
        recognition.pop("stt_model_sha256")
    else:
        physical["stt_model_sha256"] = "b" * 64
    for name, value in (("recognition", recognition), ("actions", actions), ("physical", physical)):
        write(session.parent / (name + ".json"), value)
    result = voice.evaluate(session, session.parent / "aggregate.json")
    assert not result["qualified"]
    assert result["recognition_and_corrected_actions_are_separate"]


def test_model_identity_changes_with_actual_asset_bytes_and_rejects_links(tmp_path):
    model = tmp_path / "model"
    model.mkdir()
    (model / "model.bin").write_bytes(b"fake model fixture")
    write(model / "config.json", {})
    original = model_identity(model)
    write(model / "config.json", {"changed": True})
    assert model_identity(model) != original
    (model / "tokenizer.json").symlink_to(model / "config.json")
    with pytest.raises(ValueError, match="unlinked"):
        model_identity(model)


def test_protocol_without_predeclared_assets_stays_pending(session):
    protocol = json.loads(session.read_text())
    protocol["stt_model_sha256"] = None
    write(session, protocol)
    reports(session)
    result = voice.evaluate(session, session.parent / "aggregate.json")
    assert not result["checks"]["stt_asset_identity"] and not result["qualified"]
