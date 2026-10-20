"""Portable voice/readiness checks; no microphone, inference or real corpus."""

import json
import types

import pytest

from victus.models.contracts import ErrorCode, ModelError, ModelPin
from victus.runtime import readiness
from victus.voice import qualification_session as voice

PIN = "a" * 64


def write(path, value):
    path.write_text(json.dumps(value))
    return path


def labels():
    return [
        {
            "id": f"{condition}-{index}",
            "language": "en",
            "condition": condition,
            "audio": f"audio/{condition}-{index}.wav",
            "reference": "synthetic label",
            "intent": "fs.create_note",
            "target": f"{condition}-{index}.txt",
        }
        for condition in ("quiet", "noisy")
        for index in range(50)
    ] + [
        {
            "id": name,
            "language": "en",
            "condition": name,
            "audio": f"audio/{name}.wav",
            "reference": "",
            "intent": None,
            "target": None,
        }
        for name in ("silence", "background", "assistant_speech")
    ]


def limits():
    return {
        "quiet": {
            "max_word_error_rate": 0.2,
            "min_intent_accuracy": 0.9,
            "min_target_accuracy": 0.9,
            "min_action_accuracy": 0.9,
        },
        "noisy": {
            "max_word_error_rate": 0.4,
            "min_intent_accuracy": 0.8,
            "min_target_accuracy": 0.8,
            "min_action_accuracy": 0.8,
        },
        "max_negative_proposals": 0,
    }


@pytest.fixture
def session(tmp_path, monkeypatch):
    monkeypatch.setattr(voice, "runtime_identity", lambda: PIN)
    manifest = write(tmp_path / "manifest.json", labels())
    thresholds = write(tmp_path / "thresholds.json", limits())
    model = tmp_path / "model"
    model.mkdir()
    (model / "model.bin").write_bytes(b"synthetic asset identity only")
    write(model / "config.json", {})
    return voice.prepare(manifest, thresholds, tmp_path / "private-session", model=model)


def reports(protocol):
    root = protocol.parent
    value = json.loads(protocol.read_text())
    identity = {
        "runtime_sha256": PIN,
        "runtime_end_sha256": PIN,
        "manifest_sha256": value["manifest_sha256"],
    }
    recognition = {
        **identity,
        "stt_model_sha256": value["stt_model_sha256"],
        "groups": {
            condition: {
                "samples": 50,
                "word_error_rate": 0.1,
                "intent_accuracy": 1.0,
                "target_accuracy": 1.0,
            }
            for condition in ("quiet", "noisy")
        },
    }
    recognition["groups"].update(
        {
            name: {"samples": 1, "non_command_with_proposal": 0}
            for name in ("silence", "background", "assistant_speech")
        }
    )
    actions = {
        **identity,
        "groups": {
            condition: {
                "measured": 50,
                "unmeasured": 0,
                "accuracy": 1.0,
                "corrections_measured": 50,
                "corrected_reviews": 5,
                "correction_rate": 0.1,
            }
            for condition in ("quiet", "noisy")
        },
    }
    physical = {
        "runtime_sha256": PIN,
        "runtime_end_sha256": PIN,
        "human_witnessed": True,
        "stt_model_sha256": value["stt_model_sha256"],
        "checks": dict.fromkeys(voice.PHYSICAL_CHECKS, True),
    }
    for name, report in (
        ("recognition", recognition),
        ("actions", actions),
        ("physical", physical),
    ):
        write(root / (name + ".json"), report)
    return recognition, actions, physical


def test_voice_prepare_creates_pending_protocol_without_audio_or_tasks(session):
    protocol = json.loads(session.read_text())
    assert protocol["qualification"] == "pending_real_recordings_and_observations"
    assert not list(session.parent.rglob("*.wav"))
    assert not list(session.parent.rglob("*.sqlite3"))
    assert json.loads((session.parent / "physical.json").read_text())["human_witnessed"] is False


@pytest.mark.parametrize("change", ["bool", "nan", "missing", "negative_limit"])
def test_voice_thresholds_must_be_predeclared_finite_and_complete(tmp_path, monkeypatch, change):
    monkeypatch.setattr(voice, "runtime_identity", lambda: PIN)
    values = limits()
    if change == "bool":
        values["quiet"]["min_action_accuracy"] = True
    elif change == "nan":
        values["quiet"]["max_word_error_rate"] = float("nan")
    elif change == "missing":
        del values["noisy"]["min_target_accuracy"]
    else:
        values["max_negative_proposals"] = -1
    with pytest.raises(ValueError):
        voice.prepare(
            write(tmp_path / "labels.json", labels()),
            write(tmp_path / "limits.json", values),
            tmp_path / "session",
        )


def test_complete_voice_reports_keep_recognition_and_reviewed_actions_separate(session):
    reports(session)
    result = voice.evaluate(session, session.parent / "summary.json")
    assert result["qualified"] is True
    assert result["recognition_and_corrected_actions_are_separate"] is True
    assert result["operator_pairing_and_witness_limitations"] is True
    with pytest.raises(FileExistsError):
        voice.evaluate(session, session.parent / "summary.json")


@pytest.mark.parametrize(
    "change",
    [
        "missing",
        "wrong_runtime",
        "partial_actions",
        "unwitnessed",
        "bool_metric",
        "bad_negatives",
        "empty_negatives",
    ],
)
def test_missing_or_invalid_voice_evidence_never_qualifies(session, change):
    recognition, actions, physical = reports(session)
    if change == "missing":
        (session.parent / "actions.json").unlink()
    elif change == "wrong_runtime":
        recognition["runtime_end_sha256"] = "b" * 64
    elif change == "partial_actions":
        actions["groups"]["quiet"]["measured"] = 49
        actions["groups"]["quiet"]["unmeasured"] = 1
    elif change == "unwitnessed":
        physical["human_witnessed"] = False
    elif change == "bool_metric":
        recognition["groups"]["quiet"]["intent_accuracy"] = True
    elif change == "bad_negatives":
        recognition["groups"]["background"]["non_command_with_proposal"] = 1
    else:
        recognition["groups"]["silence"] = {}
    for name, report in (("recognition", recognition), ("physical", physical)):
        write(session.parent / (name + ".json"), report)
    if change != "missing":
        write(session.parent / "actions.json", actions)
    assert voice.evaluate(session, session.parent / "summary.json")["qualified"] is False


def test_changed_voice_manifest_rejected(session):
    reports(session)
    (session.parent / "manifest.json").write_text("[]")
    with pytest.raises(ValueError, match="Unchanged"):
        voice.evaluate(session, session.parent / "summary.json")


class FakeOllama:
    models = []
    error = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def list_models(self):
        if self.error:
            raise self.error
        return self.models


@pytest.fixture
def inventory_env(tmp_path, monkeypatch):
    monkeypatch.setattr(readiness, "runtime_identity", lambda: PIN)
    monkeypatch.setattr(readiness, "gpu_memory", lambda: None)
    monkeypatch.setattr(readiness, "OllamaClient", FakeOllama)
    monkeypatch.setattr(
        FakeOllama, "models", [ModelPin(name="candidate:4b", digest="sha256:" + PIN)]
    )
    monkeypatch.setattr(FakeOllama, "error", None)
    return tmp_path / "readiness.json"


def test_inventory_selects_exact_pin_without_claiming_inference(inventory_env):
    result = readiness.inventory(inventory_env, model="candidate:4b")
    assert result["selected_pin"]["digest"] == "sha256:" + PIN
    assert result["inference_qualified"] is False
    assert result["model_downloaded"] is False and result["cloud_used"] is False
    assert result["resource_ready"] is True


def test_inventory_unknown_model_and_unavailable_service_are_explicit(inventory_env, monkeypatch):
    result = readiness.inventory(inventory_env, model="not-installed")
    assert (
        result["selected_pin"] is None and result["model_error"] == "EXACT_INSTALLED_MODEL_REQUIRED"
    )
    monkeypatch.setattr(FakeOllama, "error", ModelError(ErrorCode.UNAVAILABLE))
    result = readiness.inventory(inventory_env.with_name("unavailable.json"))
    assert result["model_service_available"] is False and result["inference_qualified"] is False


def test_inventory_unknown_resources_remains_unready(inventory_env, monkeypatch):
    from victus.runtime.resources import ResourcePressure

    def blocked():
        raise ResourcePressure("LOCAL_RESOURCE_TELEMETRY_UNAVAILABLE")

    monkeypatch.setattr(
        readiness, "resources", lambda: types.SimpleNamespace(check_current=blocked)
    )
    monkeypatch.setattr(readiness, "system_memory", lambda: None)
    result = readiness.inventory(inventory_env)
    assert result["resource_ready"] is False and result["memory"] is None
