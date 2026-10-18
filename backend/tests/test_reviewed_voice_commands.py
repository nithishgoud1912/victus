import time

import pytest
from pydantic import ValidationError
from test_voice import review, voice_service

from victus.agent.commands import CommandFields, CommandSubmission
from victus.storage.secure_json import decode
from victus.voice.action_evaluation import verify_case
from victus.voice.contracts import ReviewedSubmission, VoiceState
from victus.voice.service import VoiceConflict

pytest_plugins = ["test_voice"]


def completed(tasks, task_id):
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        result = tasks.database.get(task_id)
        if result.status not in {"queued", "prepared", "running", "waiting_for_review"}:
            return result
        time.sleep(0.02)
    raise AssertionError("Reviewed command did not finish")


def test_reviewed_missing_values_use_shared_durable_intake_and_verifier(services):
    voice = voice_service(services)
    snapshot = review(voice)
    pending = voice.submit(
        snapshot.session_id, snapshot.revision, CommandSubmission(text="Create a note")
    )
    assert pending.state == VoiceState.CLARIFYING and pending.command.state == "clarification"
    assert not services.tasks.database.list_tasks()
    assert services.commands.get(pending.command.command_id).missing == ["filename", "content"]
    submitted = voice.clarify(
        pending.session_id,
        pending.revision,
        CommandFields(filename="spoken.txt", content="Private literal <img>"),
    )
    with pytest.raises(VoiceConflict):
        voice.clarify(
            pending.session_id,
            pending.revision,
            CommandFields(filename="other.txt", content="other"),
        )
    assert completed(services.tasks, submitted.task_id).verified
    assert services.tasks.database.get(submitted.task_id).tool.startswith("internal.command.")
    row = services.commands.get_row(submitted.command.command_id)
    assert decode(row["payload"])["origin"] == "voice"
    assert verify_case(
        services.settings.data_dir,
        submitted.command.command_id,
        "create note spoken.txt with text Private literal <img>",
    )
    (services.settings.workspace / "spoken.txt").write_text("changed")
    assert not verify_case(
        services.settings.data_dir,
        submitted.command.command_id,
        "create note spoken.txt with text Private literal <img>",
    )
    with pytest.raises(ValueError, match="server-owned"):
        services.commands.submit(CommandSubmission(text="Create a note"), row["request_id"])


def test_spoken_native_intent_never_grants_save_authority(services):
    voice = voice_service(services)
    snapshot = review(voice)
    pending = voice.submit(
        snapshot.session_id,
        snapshot.revision,
        CommandSubmission(text='create checklist study.txt with items ["Inspect"]'),
    )
    assert pending.state == VoiceState.CLARIFYING and pending.command.state == "unavailable"
    assert not services.tasks.database.list_tasks()
    services.stop()
    assert voice.snapshot().command is None
    with pytest.raises(VoiceConflict):
        voice.clarify(pending.session_id, pending.revision, CommandFields())


def test_voice_clarification_expires_and_never_submits_after_cancel(services):
    voice = voice_service(services)
    snapshot = review(voice)
    pending = voice.submit(
        snapshot.session_id, snapshot.revision, CommandSubmission(text="Create a note")
    )
    voice.review_deadline = 0
    assert voice.snapshot().error_code == "TRANSCRIPT_REVIEW_EXPIRED"
    with pytest.raises(VoiceConflict):
        voice.clarify(
            pending.session_id, pending.revision, CommandFields(filename="late.txt", content="no")
        )
    assert not services.tasks.database.list_tasks()


@pytest.mark.parametrize(
    "extra",
    [
        {"approved": True},
        {"command": {"text": "x", "origin": "voice"}},
        {"action": {"tool": "shell.run", "arguments": {}}},
    ],
)
def test_review_transport_cannot_assert_authority_or_origin(extra):
    with pytest.raises(ValidationError):
        ReviewedSubmission.model_validate(
            {"session_id": "s", "revision": 1, "confirmation": "explicit_user_review", **extra}
        )


def test_missing_local_model_keeps_capture_unavailable(services):
    from victus.voice.service import VoiceService

    voice = VoiceService(services.tasks, services.settings.data_dir / "missing-model")
    assert not voice.snapshot().enabled
    with pytest.raises(VoiceConflict):
        voice.start()
    voice.close()


def test_authenticated_voice_command_and_clarification_routes(tmp_path):
    from fastapi.testclient import TestClient
    from test_voice import TOKEN

    from victus.api.app import create_app
    from victus.settings import Settings

    with TestClient(
        create_app(Settings(tmp_path / "api", TOKEN)), base_url="http://127.0.0.1"
    ) as client:
        services = client.app.state.services
        voice = voice_service(services)
        snapshot = review(voice)
        headers = {"Authorization": "Bearer " + TOKEN}
        body = {
            "session_id": snapshot.session_id,
            "revision": snapshot.revision,
            "command": {"text": "Create a note"},
        }
        assert client.post("/api/voice/submit", headers=headers, json=body).status_code == 422
        pending = client.post(
            "/api/voice/submit",
            headers=headers,
            json={**body, "confirmation": "explicit_user_review"},
        ).json()
        assert pending["state"] == "clarifying"
        assert (
            client.get("/api/voice", headers=headers).json()["command"]["command_id"]
            == pending["command"]["command_id"]
        )
        clarification = {
            "session_id": pending["session_id"],
            "revision": pending["revision"],
            "fields": {"filename": "http-voice.txt", "content": "reviewed"},
        }
        assert (
            client.post("/api/voice/clarify", headers=headers, json=clarification).status_code
            == 422
        )
        clarification["confirmation"] = "explicit_user_review"
        response = client.post("/api/voice/clarify", headers=headers, json=clarification)
        assert response.status_code == 200, response.text
        assert completed(services.tasks, response.json()["task_id"]).verified
        assert (
            client.post("/api/voice/clarify", headers=headers, json=clarification).status_code
            == 409
        )


def test_action_evaluation_keeps_unmeasured_cases_out_of_accuracy(tmp_path):
    import json

    from victus.voice.action_evaluation import evaluate

    labels = [
        {
            "id": f"{condition}_{index}",
            "condition": condition,
            "language": "en",
            "reference": "create note voice.txt with text reviewed",
        }
        for condition in ["quiet", "noisy"]
        for index in range(50)
    ]
    manifest = tmp_path / "labels.json"
    manifest.write_text(json.dumps(labels))
    bindings = tmp_path / "bindings.json"
    bindings.write_text("{}")
    report = evaluate(manifest, bindings, tmp_path / "unused-runtime")
    assert not report["complete"]
    assert all(
        group["measured"] == 0 and group["accuracy"] is None and group["unmeasured"] == 50
        for group in report["groups"].values()
    )
