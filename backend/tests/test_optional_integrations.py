"""M8 contracts with fake network/audio; real pinned local MCP subprocess."""

import asyncio
import json
import threading
import time
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient

from victus.adapters.mcp.client import LocalMCPClient, MCPError
from victus.adapters.mcp.discovery import discover
from victus.adapters.mcp.mapping import mcp_create_note, validate_result
from victus.api.app import create_app
from victus.models.cloud import CloudProvider
from victus.models.cloud_service import CloudService
from victus.models.contracts import (
    ErrorCode,
    ModelError,
    ModelPin,
    ProviderMessage,
    ProviderRequest,
)
from victus.models.gateway import ModelGateway, RequestBudget
from victus.models.transfer_policy import ConsentRequired, TransferPolicy
from victus.settings import Settings
from victus.tools.contracts import NoteArguments
from victus.tools.filesystem import fs_create_note
from victus.voice.capture import MicrophoneCapture
from victus.voice.wake import Asset, WakeConfiguration, WakeListener, load_qualified

PIN = ModelPin(name="fixture/model", digest="sha256:" + "a" * 64)


def request(pin=PIN):
    return ProviderRequest(pin=pin, messages=[ProviderMessage(role="user", content="private test")],
                           output_schema={"type": "object"}, max_output_tokens=32)


class Credentials:
    calls = 0

    def read(self):
        self.calls += 1
        return "fixture-secret-key"


def response():
    return {"model": PIN.name, "choices": [{"finish_reason": "stop", "message": {
        "role": "assistant", "content": '{}'}}],
        "usage": {"prompt_tokens": 9, "completion_tokens": 2}}


def authorized_provider(handler):
    policy = TransferPolicy()
    credentials = Credentials()
    provider = CloudProvider(PIN, "SelectedProvider", policy, credentials,
                             transport=httpx.MockTransport(handler))
    preview = provider.preview(request())
    policy.decide(preview.id, approve=True, confirmation="explicit_user_review")
    provider.consent_id = preview.id
    return provider


def test_exact_consent_expiry_denial_replay_and_capacity():
    now = [0.0]
    policy = TransferPolicy(clock=lambda: now[0], lifetime=1)
    p = policy.preview("recipient", {"private": "exact"})
    assert "exact" in p.body
    policy.decide(p.id, approve=True, confirmation="explicit_user_review")
    with pytest.raises(ConsentRequired):
        policy.consume(p.id, "other recipient", {"private": "exact"})
    with pytest.raises(ConsentRequired):
        policy.consume(p.id, "recipient", {"private": "exact"})
    p = policy.preview("recipient", {})
    policy.decide(p.id, approve=False, confirmation="explicit_user_review")
    with pytest.raises(ConsentRequired):
        policy.consume(p.id, "recipient", {})
    p = policy.preview("recipient", {})
    now[0] = 2
    with pytest.raises(ConsentRequired):
        policy.decide(p.id, approve=True, confirmation="explicit_user_review")
    for _ in range(8):
        policy.preview("recipient", {})
    with pytest.raises(ValueError):
        policy.preview("recipient", {})


def test_cloud_denial_never_reads_credentials_or_sends():
    calls = []
    credentials = Credentials()
    provider = CloudProvider(PIN, "SelectedProvider", TransferPolicy(), credentials,
                             transport=httpx.MockTransport(lambda r: calls.append(r)))
    with pytest.raises(ModelError) as error:
        asyncio.run(provider.complete(request()))
    assert error.value.error.code == ErrorCode.CONSENT
    assert credentials.calls == 0 and calls == []


def test_cloud_gateway_budget_and_one_use_transfer():
    calls = []

    def handler(r):
        body = json.loads(r.content)
        assert body["provider"]["allow_fallbacks"] is False
        assert body["provider"]["order"] == ["SelectedProvider"]
        assert "fixture-secret-key" not in r.content.decode()
        calls.append(r)
        return httpx.Response(200, json=response())

    provider = authorized_provider(handler)
    budget = RequestBudget(max_requests=1, max_output_tokens=32)
    gateway = ModelGateway(provider, budget)
    assert asyncio.run(gateway.request(request())).content == '{}'
    with pytest.raises(ModelError):
        asyncio.run(gateway.request(request()))
    assert len(calls) == 1 and budget.snapshot()["requests"] == 1
    with pytest.raises(ModelError):
        asyncio.run(provider.complete(request()))
    assert len(calls) == 1


def test_changed_request_requires_fresh_consent():
    calls = []
    provider = authorized_provider(lambda r: calls.append(r))
    changed = request().model_copy(update={"max_output_tokens": 31})
    with pytest.raises(ModelError):
        asyncio.run(provider.complete(changed))
    assert calls == [] and provider.credentials.calls == 0


@pytest.mark.parametrize("change", ["tools", "model", "usage", "finish", "oversize", "invalid"])
def test_cloud_rejects_malformed_or_expanded_output(change):
    value = response()
    if change == "tools":
        value["choices"][0]["message"]["tool_calls"] = [{"name": "shell"}]
    elif change == "model":
        value["model"] = "other/model"
    elif change == "usage":
        value["usage"]["completion_tokens"] = True
    elif change == "finish":
        value["choices"][0]["finish_reason"] = "length"
    elif change == "oversize":
        value["padding"] = "x" * 200001
    provider = authorized_provider(lambda r: httpx.Response(
        200, content=b"not json" if change == "invalid" else json.dumps(value).encode()))
    with pytest.raises(ModelError) as error:
        asyncio.run(provider.complete(request()))
    assert error.value.error.code == ErrorCode.PROTOCOL
    assert "private test" not in str(error.value)


@pytest.mark.parametrize("case", ["quota", "timeout", "redirect"])
def test_cloud_dependency_failures_are_bounded_and_visible(case):
    calls = []

    def handler(r):
        calls.append(r)
        if case == "timeout":
            raise httpx.ReadTimeout("private remote body")
        return httpx.Response(429 if case == "quota" else 302,
                              headers={"Location": "https://unselected.invalid"})

    provider = authorized_provider(handler)
    with pytest.raises(ModelError):
        asyncio.run(provider.complete(request()))
    assert len(calls) == 1
    assert provider.dependency_state == {
        "quota": "quota_exhausted", "timeout": "timeout", "redirect": "unavailable"}[case]


def test_cloud_service_denial_and_stop_clear_pending():
    stopped = threading.Event()
    service = CloudService("fixture/model", "SelectedProvider", stopped)
    preview = service.preview(request(service.pin))
    assert asyncio.run(service.review(preview.id, approve=False,
                                      confirmation="explicit_user_review")) is None
    with pytest.raises(ConsentRequired):
        asyncio.run(service.review(preview.id, approve=True, confirmation="explicit_user_review"))
    stopped.set()
    with pytest.raises(ModelError):
        service.preview(request(service.pin))


@pytest.mark.parametrize("factory", [fs_create_note, mcp_create_note])
def test_native_and_mcp_note_contract(factory, tmp_path):
    spec = factory()
    args = NoteArguments(filename="contract.txt", text="independently verified")
    path = spec.execute(tmp_path, args)
    assert spec.verify(path, args)
    assert path.parent == tmp_path
    path.write_text("tampered")
    assert not spec.verify(path, args)
    assert spec.name == "fs.create_note" and spec.required_scope == "fs:write"


@pytest.mark.parametrize("factory", [fs_create_note, mcp_create_note])
def test_adapter_does_not_overwrite(factory, tmp_path):
    args = NoteArguments(filename="existing.txt", text="new")
    (tmp_path / args.filename).write_text("original")
    with pytest.raises(FileExistsError):
        factory().execute(tmp_path, args)
    assert (tmp_path / args.filename).read_text() == "original"


@pytest.mark.parametrize("mutate", ["extra", "schema", "scope"])
def test_mcp_discovery_disables_unconstrained_tools(mutate):
    tool = {"name": "create_note", "inputSchema": NoteArguments.model_json_schema()}
    tools = [tool]
    if mutate == "extra":
        tools.append({"name": "shell"})
    elif mutate == "schema":
        tool["inputSchema"] = {"type": "object"}
    else:
        tool["scope"] = "*"
    with pytest.raises(MCPError):
        discover(SimpleNamespace(call=lambda *a: {"tools": tools}))


@pytest.mark.parametrize("value", [None, {}, {"isError": True, "content": []},
    {"isError": False, "content": [{"type": "text", "text": '{"filename":"../escape"}'}]},
    {"isError": False, "content": [{"type": "text", "text": "x" * 1025}]}])
def test_mcp_output_never_grants_authority(value):
    with pytest.raises(MCPError):
        validate_result(value, NoteArguments(filename="safe.txt", text="safe"))


def test_mcp_deadline_cancel_and_process_cleanup(tmp_path):
    client = LocalMCPClient(tmp_path, timeout=0.001)
    with pytest.raises(MCPError):
        with client:
            pass
    if client.process:
        assert client.process.poll() is not None
    cancelled = threading.Event()
    cancelled.set()
    with pytest.raises(MCPError):
        with LocalMCPClient(tmp_path, cancelled=cancelled):
            pass


def test_mcp_rejects_server_source_drift(tmp_path, monkeypatch):
    monkeypatch.setattr("victus.adapters.mcp.client.REFERENCE_SHA256", "0" * 64)
    with pytest.raises(MCPError, match="PIN_MISMATCH"):
        with LocalMCPClient(tmp_path):
            pass


def test_mcp_stalled_tool_response_obeys_deadline_and_reaps_child(tmp_path, monkeypatch):
    client = LocalMCPClient(tmp_path)
    with pytest.raises(MCPError, match="MCP_TIMEOUT"):
        with client:
            client.deadline = time.monotonic() + 0.03
            monkeypatch.setattr(client, "_write", lambda message: None)
            client.call("tools/call", {})
    assert client.process.poll() is not None


def test_wake_manifest_requires_real_evidence(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_text('{}')
    with pytest.raises(ValueError):
        load_qualified(path)
    asset = Asset(path=str(tmp_path / "missing.onnx"), sha256="a" * 64)
    config = WakeConfiguration(wake=asset, melspectrogram=asset, embedding=asset,
                               threshold=0.5, cooldown_seconds=3.0, command_seconds=6.0)
    path.write_text(json.dumps({"configuration": config.model_dump(), "qualification": {
        "positive_clips": 99, "negative_seconds": 7199, "human_reviewed": True}}))
    with pytest.raises(ValueError, match="QUALIFICATION"):
        load_qualified(path)


def fake_voice():
    voice = SimpleNamespace(tasks=SimpleNamespace(stopped=threading.Event()),
        snapshot_value=SimpleNamespace(enabled=True, state="idle"),
        playback=SimpleNamespace(wake_suppressed=False), thread=None, calls=[])

    def start(**kwargs):
        assert not MicrophoneCapture._owner.locked()
        voice.calls.append(kwargs)
        voice.snapshot_value.state = "reviewing"

    voice.start = start
    return voice


class Stream:
    def __init__(self, **kwargs):
        self.callback, self.active = kwargs["callback"], False

    def start(self):
        self.active = True
        self.callback(b"\0" * 2560, 1280, None, False)

    def abort(self):
        self.active = False

    def close(self):
        pass


def test_wake_only_opens_short_capture_then_waits_for_review():
    voice = fake_voice()
    detector = SimpleNamespace(reset=lambda: None, score=lambda pcm: 0.9)
    listener = WakeListener(voice, detector_factory=lambda c: detector, stream_factory=Stream)
    listener.config = SimpleNamespace(threshold=0.5, cooldown_seconds=1, command_seconds=6)
    listener.enable()
    deadline = time.monotonic() + 2
    while not voice.calls and time.monotonic() < deadline:
        time.sleep(0.005)
    listener.disable()
    assert voice.calls == [{"from_wake": True, "command_seconds": 6}]
    assert not listener.listening and not MicrophoneCapture._owner.locked()


def test_wake_playback_and_stop_suppress_listening():
    voice = fake_voice()
    voice.playback.wake_suppressed = True
    listener = WakeListener(voice, detector_factory=lambda c: None,
                            stream_factory=lambda **k: pytest.fail("Must not open microphone"))
    listener.config = SimpleNamespace()
    listener.enable()
    time.sleep(0.06)
    voice.tasks.stopped.set()
    listener.disable()
    assert voice.calls == []


def test_default_api_keeps_optional_features_disabled(tmp_path):
    settings = Settings(tmp_path, "x" * 40)
    with TestClient(create_app(settings), base_url="http://127.0.0.1") as client:
        headers = {"Authorization": "Bearer " + settings.api_token}
        status = client.get("/api/integrations", headers=headers).json()
        assert status["cloud"] == "disabled" and status["mcp_notes"] is False
        assert client.post("/api/voice/wake/enable", headers=headers).status_code == 409
        assert client.get("/api/health", headers=headers).status_code == 200
        assert client.get("/api/integrations").status_code == 401


def test_mcp_runs_through_supervised_task_service(tmp_path):
    settings = Settings(tmp_path, "x" * 40, mcp_notes=True)
    with TestClient(create_app(settings), base_url="http://127.0.0.1") as client:
        headers = {"Authorization": "Bearer " + settings.api_token}
        queued = client.post("/api/tasks", headers=headers, json={
            "tool": "fs.create_note", "arguments": {"filename": "supervised.txt", "text": "MCP worker"},
        })
        assert queued.status_code == 202
        task_id = queued.json()["task_id"]
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            result = client.get(f"/api/tasks/{task_id}", headers=headers).json()
            if result["status"] not in {"queued", "prepared", "running"}:
                break
            time.sleep(0.02)
        assert result["status"] == "succeeded" and result["verified"], result
        assert (settings.workspace / "supervised.txt").read_text() == "MCP worker"


def test_cloud_api_review_and_stop_are_explicit(tmp_path):
    settings = Settings(tmp_path, "x" * 40, cloud_model="fixture/model",
                        cloud_upstream="SelectedProvider")
    with TestClient(create_app(settings), base_url="http://127.0.0.1") as client:
        headers = {"Authorization": "Bearer " + settings.api_token}
        service = client.app.state.services.cloud
        credentials = Credentials()
        service.credentials = credentials
        status = client.get("/api/integrations", headers=headers).json()
        assert status["cloud_pin"] == service.pin.model_dump()
        preview = client.post("/api/integrations/cloud/preview", headers=headers,
                              json=request(service.pin).model_dump()).json()
        assert "private test" in preview["body"] and credentials.calls == 0
        body = {"id": preview["id"], "approve": False, "confirmation": "explicit_user_review"}
        assert client.post("/api/integrations/cloud/review", headers=headers, json=body).status_code == 200
        assert client.post("/api/integrations/cloud/review", headers=headers, json=body).status_code == 409
        assert credentials.calls == 0
        second = client.post("/api/integrations/cloud/preview", headers=headers,
                             json=request(service.pin).model_dump()).json()
        client.post("/api/stop", headers=headers)
        body.update(id=second["id"], approve=True)
        assert client.post("/api/integrations/cloud/review", headers=headers, json=body).status_code == 409
        assert credentials.calls == 0


@pytest.mark.parametrize("kind", ["disconnect", "overflow"])
def test_wake_input_failure_closes_stream_and_never_opens_command(kind):
    voice = fake_voice()

    class FailedStream(Stream):
        def start(self):
            self.active = kind != "disconnect"
            if kind == "overflow":
                for _ in range(40):
                    self.callback(b"\0" * 2560, 1280, None, False)

    detector = SimpleNamespace(reset=lambda: None, score=lambda pcm: 0.9)
    listener = WakeListener(voice, detector_factory=lambda c: detector, stream_factory=FailedStream)
    listener.config = SimpleNamespace(threshold=0.5, cooldown_seconds=1, command_seconds=6)
    listener.enable()
    listener.thread.join(timeout=1)
    assert listener.error == "WAKE_LISTENER_UNAVAILABLE"
    assert voice.calls == [] and not MicrophoneCapture._owner.locked()
