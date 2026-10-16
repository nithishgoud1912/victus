"""Deterministic M6 qualification. No physical recording or real model downloads."""

import sys
import threading
import time
import types

import pytest
from fastapi.testclient import TestClient

from victus.api.app import create_app
from victus.bootstrap import build_services
from victus.settings import Settings
from victus.tools.contracts import ActionRequest, NoteArguments
from victus.voice.audio import float32_to_pcm16, pcm16_mono, resample_pcm16
from victus.voice.capture import MicrophoneCapture
from victus.voice.contracts import VoiceState
from victus.voice.playback import Playback
from victus.voice.service import VoiceConflict, VoiceService
from victus.voice.stt import LocalTranscriber, TranscriptionWorker
from victus.voice.transcript_review import review_transcript

TOKEN = "fixture-only-" + "x" * 40
ACTION = ActionRequest(
    tool="fs.create_note", arguments=NoteArguments(filename="voice.txt", text="reviewed")
)


class FakeCapture:
    def __init__(self, *, speech=True):
        self.done = threading.Event()
        self.ready = threading.Event()
        self.had_voice, self.error, self.sample_rate = speech, None, 16000
        self.closed = False
        self.cleared = False

    def start(self):
        self.ready.set()

    def finish(self):
        self.done.set()

    def check_limits(self):
        pass

    def close(self):
        self.closed = True

    def clear(self):
        self.cleared = True

    def audio(self):
        return b"\x00\x20" * 800


class FakeSTT:
    def __init__(self, text="create note voice.txt with text reviewed", block=False):
        self.text, self.block = text, block
        self.started = threading.Event()
        self.calls = 0

    def transcribe(self, pcm, cancel):
        self.calls += 1
        self.started.set()
        if self.block:
            cancel.wait(2)
        return self.text

    def close(self):
        pass


class FakeOutput:
    def __init__(self):
        self.started, self.finished = threading.Event(), threading.Event()
        self.text = None

    def speak(self, text, interrupted, deadline):
        self.text = text
        self.started.set()
        interrupted.wait(max(0, deadline - time.monotonic()))
        self.finished.set()


def wait_state(voice, state, timeout=3):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        snapshot = voice.snapshot()
        if snapshot.state == state:
            return snapshot
        time.sleep(0.005)
    raise AssertionError(f"Expected {state}, got {voice.snapshot().model_dump()}")


@pytest.fixture
def services(tmp_path):
    result = build_services(Settings(tmp_path / "runtime", TOKEN))
    yield result
    result.close()


def voice_service(services, **kwargs):
    services.voice.close()
    services.voice = VoiceService(
        services.tasks,
        capture_factory=FakeCapture,
        transcriber=FakeSTT(),
        playback=Playback(FakeOutput()),
        **kwargs,
    )
    return services.voice


def review(voice):
    recording = voice.start()
    assert voice.capture.ready.wait(1)
    voice.finish(recording.session_id, recording.revision)
    return wait_state(voice, VoiceState.REVIEWING)


@pytest.mark.parametrize(
    "text", ["", "...", "[silence]", "[music]", "thanks for watching", "uh", "[noise]"]
)
def test_non_speech_rejected(text):
    assert not review_transcript(text).accepted


@pytest.mark.parametrize(
    "text",
    [
        "delete that",
        "create note it with text hello",
        "open the other document",
        "approve once",
        "create note ../bad.txt with text hello",
    ],
)
def test_ambiguous_and_unsupported_targets_need_clarification(text):
    result = review_transcript(text)
    assert result.accepted and result.action is None and result.clarification


def test_exact_target_parsed_but_never_submitted_by_parser():
    result = review_transcript("create note voice.txt with text reviewed")
    assert result.action == ACTION


def test_pcm_formats_and_resampling():
    data = float32_to_pcm16([-1, 0, 1, 2])
    assert list(pcm16_mono(data)) == [-32767, 0, 32767, 32767]
    assert list(pcm16_mono(b"\x00\x10\x00\x20", 2)) == [6144]
    assert len(resample_pcm16(data, 32000)) == 4
    with pytest.raises(ValueError):
        pcm16_mono(b"x")
    with pytest.raises(ValueError):
        float32_to_pcm16([float("nan")])


class FakeStream:
    def __init__(self, **kwargs):
        self.callback = kwargs["callback"]
        self.active = False

    def start(self):
        self.active = True

    def abort(self):
        self.active = False

    def close(self):
        pass


def test_single_microphone_ring_limit_and_release():
    clock = [0.0]
    capture = MicrophoneCapture(max_seconds=4, stream_factory=FakeStream, clock=lambda: clock[0])
    capture.start()
    other = MicrophoneCapture(stream_factory=FakeStream)
    try:
        with pytest.raises(RuntimeError, match="MICROPHONE_BUSY"):
            other.start()
        for _ in range(250):
            capture._callback(b"\x00\x20" * 320, 320, None, False)
        assert capture.size <= capture.max_bytes
        assert len(capture.audio()) <= capture.max_bytes
        clock[0] = 4
        capture.check_limits()
        assert capture.done.is_set()
    finally:
        capture.close()
    other.start()
    other.close()
    capture.clear()
    assert capture.size == 0 and not capture.frames


@pytest.mark.parametrize("speech, elapsed", [(False, 4.1), (True, 1.6)])
def test_finite_silence_vad(speech, elapsed):
    clock = [0.0]
    capture = MicrophoneCapture(stream_factory=FakeStream, clock=lambda: clock[0])
    capture.start()
    try:
        if speech:
            capture._callback(b"\x00\x20" * 320, 320, None, False)
        clock[0] = elapsed
        capture._callback(b"\0" * 640, 320, None, False)
        assert capture.done.is_set()
    finally:
        capture.close()


def test_disconnect_and_overflow_fail_closed():
    capture = MicrophoneCapture(stream_factory=FakeStream)
    capture.start()
    capture.stream.active = False
    capture.check_limits()
    assert capture.error == "MICROPHONE_DISCONNECTED" and capture.done.is_set()
    capture.close()
    capture = MicrophoneCapture(stream_factory=FakeStream)
    capture.start()
    capture._callback(b"\0" * 640, 320, None, True)
    assert capture.error == "AUDIO_INPUT_INTERRUPTED"
    capture.close()


def test_silence_never_reaches_inference(services):
    voice = voice_service(services)
    voice.capture_factory = lambda: FakeCapture(speech=False)
    s = voice.start()
    assert voice.capture.ready.wait(1)
    voice.finish(s.session_id, s.revision)
    assert wait_state(voice, VoiceState.ERROR).error_code == "NO_SPEECH_DETECTED"
    assert voice.transcriber.calls == 0


def test_review_required_shared_task_path_and_replay_rejected(services):
    voice = voice_service(services)
    s = review(voice)
    assert not services.tasks.database.list_tasks()
    with pytest.raises(VoiceConflict):
        voice.submit(s.session_id, s.revision - 1, ACTION)
    submitted = voice.submit(s.session_id, s.revision, ACTION)
    with pytest.raises(VoiceConflict):
        voice.submit(s.session_id, s.revision, ACTION)
    assert submitted.task_id
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        result = services.tasks.database.get(submitted.task_id)
        if result.verified:
            break
        time.sleep(0.01)
    assert result.verified
    assert (services.settings.workspace / "voice.txt").read_text() == "reviewed"
    assert voice.snapshot().transcript is None
    assert voice.snapshot().proposal is None
    events = services.events.get_events(task_id=submitted.task_id)
    assert "reviewed" not in str([e.to_dict() for e in events])


@pytest.mark.parametrize(
    "state",
    [
        VoiceState.RECORDING,
        VoiceState.TRANSCRIBING,
        VoiceState.REVIEWING,
        VoiceState.SUBMITTED,
        VoiceState.SPEAKING,
    ],
)
def test_stop_cancels_voice_from_each_active_state(services, state):
    voice = voice_service(services)
    if state == VoiceState.TRANSCRIBING:
        voice.transcriber.block = True
    s = voice.start()
    assert voice.capture.ready.wait(1)
    if state != VoiceState.RECORDING:
        voice.finish(s.session_id, s.revision)
        if state == VoiceState.TRANSCRIBING:
            assert voice.transcriber.started.wait(1)
        else:
            s = wait_state(voice, VoiceState.REVIEWING)
    if state in {VoiceState.SUBMITTED, VoiceState.SPEAKING}:
        voice.submit(s.session_id, s.revision, ACTION)
    if state == VoiceState.SPEAKING:
        for _ in range(200):
            s = voice.snapshot()
            if s.speech_pending:
                break
            time.sleep(0.01)
        voice.acknowledge(s.session_id, s.revision)
        assert voice.playback.output.started.wait(1)
    services.stop()
    assert services.tasks.stopped.is_set()
    s = voice.snapshot()
    assert s.state == VoiceState.ERROR and s.transcript is None
    assert voice.cancelled.is_set()
    assert not s.speech_pending
    with pytest.raises(VoiceConflict):
        voice.start()


@pytest.mark.parametrize("state", list(VoiceState))
def test_disconnect_transition_clears_sensitive_review_and_interrupts(services, state):
    voice = voice_service(services)
    with voice.lock:
        voice._update(state=state)
    voice.device_disconnected()
    assert voice.snapshot().error_code == "MICROPHONE_DISCONNECTED"
    assert voice.snapshot().state == VoiceState.ERROR
    assert voice.playback.interrupted.is_set()


def test_review_expiry_and_old_session_cannot_submit(services):
    voice = voice_service(services, review_seconds=0.03)
    s = review(voice)
    time.sleep(0.05)
    with pytest.raises(VoiceConflict):
        voice.submit(s.session_id, s.revision, ACTION)
    assert voice.snapshot().error_code == "TRANSCRIPT_REVIEW_EXPIRED"
    assert not services.tasks.database.list_tasks()


def test_spoken_results_require_display_ack_and_suppress_capture(services):
    voice = voice_service(services)
    s = review(voice)
    voice.submit(s.session_id, s.revision, ACTION)
    for _ in range(200):
        s = voice.snapshot()
        if s.speech_pending:
            break
        time.sleep(0.01)
    assert s.summary == "Your note was created and verified."
    assert not voice.playback.output.started.is_set()
    voice.acknowledge(s.session_id, s.revision)
    assert voice.playback.output.started.wait(1)
    assert voice.snapshot().wake_suppressed
    with pytest.raises(VoiceConflict):
        voice.acknowledge(s.session_id, s.revision)
    voice.cancel()
    with pytest.raises(VoiceConflict):
        voice.start()  # active playback or echo cooldown
    assert voice.playback.output.finished.wait(1)


def test_mute_interrupts_and_drops_pending_speech(services):
    voice = voice_service(services)
    voice.playback.play("fixture")
    assert voice.playback.output.started.wait(1)
    voice.mute(True)
    assert voice.playback.output.finished.wait(1)
    assert voice.snapshot().muted
    assert not voice.playback.play("must not speak")


def test_local_adapter_loads_local_only_and_consumes_lazy_segments(tmp_path, monkeypatch):
    (tmp_path / "model.bin").touch()
    consumed = []
    loaded = []

    class Model:
        def __init__(self, path, **kwargs):
            loaded.append(kwargs)

        def transcribe(self, audio, **kwargs):
            assert kwargs["vad_filter"] and kwargs["language"] == "en"

            def generate():
                consumed.append(True)
                yield types.SimpleNamespace(text=" hello ")
                yield types.SimpleNamespace(text="world")

            return generate(), None

    monkeypatch.setitem(sys.modules, "faster_whisper", types.SimpleNamespace(WhisperModel=Model))
    adapter = LocalTranscriber(str(tmp_path))
    assert adapter.transcribe("fixture.wav") == "hello world"
    assert adapter.transcribe("fixture2.wav") == "hello world"
    assert len(loaded) == 1 and loaded[0]["local_files_only"]
    assert loaded[0]["device"] == "cpu" and loaded[0]["compute_type"] == "int8"
    assert len(consumed) == 2
    with pytest.raises((ValueError, FileNotFoundError)):
        LocalTranscriber("download-this-model")


def fake_inference_worker(connection, model_path):
    connection.send(("ready", None))
    count = 0
    while True:
        connection.recv()
        if model_path == "block":
            time.sleep(30)
        count += 1
        connection.send(("result", str(count)))


def test_persistent_worker_load_once_and_close():
    worker = TranscriptionWorker("fixture", timeout=5, target=fake_inference_worker)
    try:
        assert worker.transcribe(b"\0\0", threading.Event()) == "1"
        pid = worker.process.pid
        assert worker.transcribe(b"\0\0", threading.Event()) == "2"
        assert worker.process.pid == pid and worker.loaded
    finally:
        worker.close()
    assert worker.process is None


def test_inference_deadline_kills_worker():
    worker = TranscriptionWorker("block", timeout=0.5, target=fake_inference_worker)
    with pytest.raises(RuntimeError, match="STT_DEADLINE_EXCEEDED"):
        worker.transcribe(b"\0\0", threading.Event())
    assert worker.process is None and not worker.loaded


def test_cancelled_inference_terminates_instead_of_late_result():
    worker = TranscriptionWorker("block", timeout=5, target=fake_inference_worker)
    cancel = threading.Event()
    timer = threading.Timer(0.3, cancel.set)
    timer.start()
    try:
        with pytest.raises(RuntimeError, match="VOICE_CANCELLED"):
            worker.transcribe(b"\0\0", cancel)
        assert worker.process is None
    finally:
        timer.join()
        worker.close()


def test_api_auth_review_confirmation_and_stop(tmp_path):
    with TestClient(
        create_app(Settings(tmp_path / "api", TOKEN)), base_url="http://127.0.0.1"
    ) as client:
        headers = {"Authorization": "Bearer " + TOKEN}
        services = client.app.state.services
        voice_service(services)
        assert client.get("/api/voice").status_code == 401
        s = client.post("/api/voice/start", headers=headers).json()
        assert services.voice.capture.ready.wait(1)
        assert client.post("/api/voice/start", headers=headers).status_code == 409
        client.post(
            "/api/voice/finish",
            headers=headers,
            json={"session_id": s["session_id"], "revision": s["revision"]},
        )
        s = wait_state(services.voice, VoiceState.REVIEWING)
        body = {"session_id": s.session_id, "revision": s.revision, "action": ACTION.model_dump()}
        assert client.post("/api/voice/submit", headers=headers, json=body).status_code == 422
        body["confirmation"] = "explicit_user_review"
        assert client.post("/api/voice/submit", headers=headers, json=body).status_code == 200
        assert client.post("/api/voice/submit", headers=headers, json=body).status_code == 409
        assert client.post("/api/stop", headers=headers).status_code == 200
        assert services.voice.cancelled.is_set()
        assert client.post("/api/voice/start", headers=headers).status_code == 409


def test_disabled_voice_is_import_safe_and_does_not_open_microphone(services):
    assert not services.voice.snapshot().enabled
    with pytest.raises(VoiceConflict):
        services.voice.start()


def test_transcript_keeps_note_punctuation():
    result = review_transcript("create note exact.txt with text Hello, world!")
    assert result.action.arguments.text == "Hello, world!"


def test_evaluation_reports_wer_intent_and_target_separately():
    from victus.voice.evaluation import score, word_errors

    assert word_errors("create note exact", "create a note exact") == (1, 3)
    report = score(
        [
            {
                "condition": "quiet",
                "word_errors": 1,
                "reference_words": 4,
                "intent_correct": 1,
                "target_correct": 0,
                "non_command_with_proposal": 0,
            }
        ]
    )
    assert report["quiet"]["word_error_rate"] == 0.25
    assert report["quiet"]["intent_accuracy"] == 1
    assert report["quiet"]["target_accuracy"] == 0


def test_evaluation_requires_labelled_corpus(tmp_path):
    from victus.voice.evaluation import evaluate

    manifest = tmp_path / "labels.json"
    manifest.write_text("[]")
    with pytest.raises(ValueError, match="50 quiet"):
        evaluate(manifest, None)


@pytest.mark.parametrize(
    "text",
    [
        "the weather is pleasant today",
        "Your note was created and verified.",
        "create note voice.txt with text overheard background command",
    ],
)
def test_background_and_assistant_speech_never_submit_without_review(services, text):
    voice = voice_service(services)
    voice.transcriber.text = text
    snapshot = review(voice)
    assert snapshot.state == VoiceState.REVIEWING
    assert not services.tasks.database.list_tasks()


def test_assistant_playback_blocks_capture_even_from_idle(services):
    voice = voice_service(services)
    assert voice.playback.play("assistant speech")
    assert voice.playback.output.started.wait(1)
    with pytest.raises(VoiceConflict, match="echo cooldown"):
        voice.start()
    assert voice.capture is None
    voice.playback.interrupt()
    assert voice.playback.output.finished.wait(1)
    with pytest.raises(VoiceConflict, match="echo cooldown"):
        voice.start()


def stuck_before_receive(connection, _model_path):
    connection.send(("ready", None))
    time.sleep(30)


def test_ipc_write_is_bounded_by_inference_deadline():
    worker = TranscriptionWorker("fixture", timeout=0.7, target=stuck_before_receive)
    with pytest.raises(RuntimeError, match="STT_DEADLINE_EXCEEDED"):
        worker.transcribe(b"\0" * 960000, threading.Event())
    assert worker.process is None


def test_sapi_owns_com_and_purges_literal_async_speech(monkeypatch):
    from victus.voice.tts import SapiSpeechOutput

    calls = []
    interrupted = threading.Event()

    class Voice:
        def Speak(self, text, flags):
            calls.append((text, flags))

        def WaitUntilDone(self, duration):
            assert duration == 25
            interrupted.set()
            return False

    monkeypatch.setitem(
        sys.modules,
        "pythoncom",
        types.SimpleNamespace(
            CoInitialize=lambda: calls.append("init"), CoUninitialize=lambda: calls.append("uninit")
        ),
    )
    monkeypatch.setitem(
        sys.modules, "win32com.client", types.SimpleNamespace(Dispatch=lambda name: Voice())
    )
    SapiSpeechOutput().speak("<tag>literal text</tag>", interrupted, time.monotonic() + 1)
    assert calls[0] == "init" and calls[-1] == "uninit"
    assert calls[1] == ("<tag>literal text</tag>", 1 | 2 | 16)
    assert ("", 1 | 2) in calls


def test_driver_close_failure_retains_exclusive_microphone_owner():
    class FailingClose(FakeStream):
        def close(self):
            raise OSError("unplugged")

    capture = MicrophoneCapture(stream_factory=FailingClose)
    capture.start()
    capture.close()
    other = MicrophoneCapture(stream_factory=FakeStream)
    try:
        assert capture.owned and capture.error == "MICROPHONE_DISCONNECTED"
        with pytest.raises(RuntimeError, match="MICROPHONE_BUSY"):
            other.start()
    finally:
        capture.stream.close = lambda: None
        capture.close()


def test_max_duration_finishes_even_without_callbacks():
    now = [0.0]
    capture = MicrophoneCapture(stream_factory=FakeStream, clock=lambda: now[0])
    capture.start()
    try:
        now[0] = 20.01
        capture.check_limits()
        assert capture.done.is_set()
    finally:
        capture.close()


def test_audio_metadata_rejects_empty_or_misaligned_driver_frames():
    capture = MicrophoneCapture(stream_factory=FakeStream)
    capture.start()
    try:
        capture._callback(b"", 320, None, False)
        assert capture.error == "INVALID_AUDIO_FRAME" and capture.size == 0
    finally:
        capture.close()


def test_cancelled_coordinator_never_opens_a_late_microphone(services):
    voice = voice_service(services)
    capture = FakeCapture()
    cancel = threading.Event()
    cancel.set()
    voice._run(cancel, capture)
    assert not capture.ready.is_set()
    assert capture.closed and capture.cleared
