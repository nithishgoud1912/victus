"""Qualified local ONNX wake detection. Detection opens capture, never a task.

The listener shares Python's microphone ownership lock with push to talk. Audio
is transient, bounded to 32 frames, and discarded during speech or task review.
"""

import hashlib
import importlib.metadata
import json
import math
import platform
import queue
import sys
import threading
import time
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from victus.runtime.resources import resources
from victus.voice.capture import MicrophoneCapture

WAKE_VERSIONS = {"openwakeword": "0.6.0", "numpy": "2.5.4", "onnxruntime": "1.31.0",
                 "scipy": "1.18.1", "scikit-learn": "1.9.1"}


class Asset(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    path: str
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")

    def validate_file(self):
        path = Path(self.path)
        if not path.is_absolute() or path.suffix != ".onnx" or not path.is_file():
            raise ValueError("WAKE_ASSET_UNAVAILABLE")
        # Audio and model assets must live outside every enclosing Git checkout.
        if any((p / ".git").exists() for p in path.resolve().parents):
            raise ValueError("WAKE_ASSET_MUST_BE_OUTSIDE_GIT")
        if path.stat().st_size > 128 * 1024**2:
            raise ValueError("WAKE_ASSET_TOO_LARGE")
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if digest != self.sha256:
            raise ValueError("WAKE_ASSET_HASH_MISMATCH")
        return path.resolve()


class WakeConfiguration(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    wake: Asset
    melspectrogram: Asset
    embedding: Asset
    threshold: float = Field(ge=0.01, le=0.99)
    cooldown_seconds: float = Field(ge=1, le=30)
    command_seconds: float = Field(ge=2, le=10)

    def identity(self):
        return hashlib.sha256(self.model_dump_json().encode()).hexdigest()


def load_qualified(path):
    raw = Path(path).read_bytes()
    if len(raw) > 65536:
        raise ValueError("WAKE_MANIFEST_TOO_LARGE")
    value = json.loads(raw)
    if set(value) != {"configuration", "qualification"}:
        raise ValueError("WAKE_QUALIFICATION_REQUIRED")
    config = WakeConfiguration.model_validate(value["configuration"])
    q = value["qualification"]
    # This is a locally reviewed evidence record, not permission to execute.
    if (q.get("configuration_sha256") != config.identity()
            or q.get("realistic_negative_audio") is not True
            or q.get("human_reviewed") is not True
            or type(q.get("positive_clips")) is not int or q["positive_clips"] < 100
            or not isinstance(q.get("negative_seconds"), (int, float))
            or not math.isfinite(q["negative_seconds"]) or q["negative_seconds"] < 7200
            or not isinstance(q.get("positive_recall"), (int, float))
            or not 0.90 <= q["positive_recall"] <= 1
            or not isinstance(q.get("false_activations_per_hour"), (int, float))
            or not 0 <= q["false_activations_per_hour"] <= 1
            or not isinstance(q.get("corpus_sha256"), str) or len(q["corpus_sha256"]) != 64):
        raise ValueError("WAKE_QUALIFICATION_REQUIRED")
    for asset in (config.wake, config.melspectrogram, config.embedding):
        asset.validate_file()
    return config


class OpenWakeWordDetector:
    def __init__(self, config):
        if platform.system() != "Windows" or sys.version_info[:2] != (3, 12):
            raise RuntimeError("WAKE_PLATFORM_NOT_QUALIFIED")
        for name, expected in WAKE_VERSIONS.items():
            if importlib.metadata.version(name) != expected:
                raise RuntimeError("WAKE_DEPENDENCY_NOT_QUALIFIED")
        from openwakeword.model import Model

        self.name = config.wake.validate_file().stem
        self.model = Model(
            wakeword_models=[str(config.wake.validate_file())], inference_framework="onnx",
            melspec_model_path=str(config.melspectrogram.validate_file()),
            embedding_model_path=str(config.embedding.validate_file()),
        )

    def score(self, pcm):
        import numpy as np

        if len(pcm) != 2560:
            raise ValueError("INVALID_WAKE_FRAME")
        score = float(self.model.predict(np.frombuffer(pcm, dtype="<i2"))[self.name])
        if not math.isfinite(score) or not 0 <= score <= 1:
            raise ValueError("INVALID_WAKE_SCORE")
        return score

    def reset(self):
        self.model.reset()


class WakeListener:
    def __init__(self, voice, manifest=None, *, detector_factory=OpenWakeWordDetector,
                 stream_factory=None):
        self.voice = voice
        self.detector_factory, self.stream_factory = detector_factory, stream_factory
        self.config = None
        self.error = None
        self.listening = False
        self.cancelled = threading.Event()
        self.thread = None
        self.guard = threading.Lock()
        if manifest:
            try:
                self.config = load_qualified(manifest)
            except Exception:
                self.error = "WAKE_QUALIFICATION_REQUIRED"

    @property
    def available(self):
        return self.config is not None and self.voice.snapshot_value.enabled

    def enable(self):
        from victus.voice.service import VoiceConflict

        with self.guard:
            if not self.available or self.voice.tasks.stopped.is_set():
                raise VoiceConflict("A qualified wake asset and local STT are required")
            if self.thread and self.thread.is_alive():
                return
            self.cancelled = threading.Event()
            self.error = None
            self.thread = threading.Thread(target=self._run, daemon=True, name="victus-wake")
            self.thread.start()

    def disable(self):
        from victus.voice.service import VoiceConflict

        with self.guard:
            self.cancelled.set()
            if self.thread and self.thread is not threading.current_thread():
                self.thread.join(timeout=1)
                if self.thread.is_alive():
                    raise VoiceConflict("Wake listener is still releasing the microphone")

    def _run(self):
        try:
            with resources().inference_slot("wake_load", self.cancelled, timeout=0.5, warm=False):
                detector = self.detector_factory(self.config)
            next_wake = 0.0
            while not self.cancelled.is_set() and not self.voice.tasks.stopped.is_set():
                s = self.voice.snapshot_value
                if (s.state not in {"idle", "error"} or self.voice.playback.wake_suppressed
                        or (self.voice.thread and self.voice.thread.is_alive())
                        or time.monotonic() < next_wake):
                    self.cancelled.wait(0.05)
                    continue
                detector.reset()
                detected = self._listen(detector)
                if detected and not self.cancelled.is_set() and not self.voice.tasks.stopped.is_set():
                    next_wake = time.monotonic() + self.config.cooldown_seconds
                    # Mic has closed before command capture. Review/submit remains explicit.
                    self.voice.start(from_wake=True, command_seconds=self.config.command_seconds)
        except Exception:
            self.error = "WAKE_LISTENER_UNAVAILABLE"
        finally:
            self.listening = False

    def _listen(self, detector):
        frames = queue.Queue(maxsize=32)
        failed = threading.Event()

        def callback(data, count, _timing, status):
            if status or count != 1280:
                failed.set()
                return
            try:
                frames.put_nowait(bytes(data))
            except queue.Full:
                failed.set()  # Dropping audio silently would invalidate detection context.

        if not MicrophoneCapture._owner.acquire(blocking=False):
            self.cancelled.wait(0.05)
            return False
        stream = None
        closed = True
        try:
            factory = self.stream_factory
            if factory is None:
                from sounddevice import RawInputStream

                factory = RawInputStream
            stream = factory(samplerate=16000, channels=1, dtype="int16", blocksize=1280,
                             callback=callback)
            closed = False
            stream.start()
            self.listening = True
            while not self.cancelled.is_set() and not self.voice.tasks.stopped.is_set():
                if failed.is_set() or not stream.active:
                    raise RuntimeError("WAKE_AUDIO_INTERRUPTED")
                if self.voice.playback.wake_suppressed:
                    return False
                try:
                    pcm = frames.get(timeout=0.05)
                except queue.Empty:
                    continue
                with resources().inference_slot("wake", self.cancelled, timeout=0.1, warm=True):
                    score = detector.score(pcm)
                if score >= self.config.threshold:
                    return True
            return False
        finally:
            self.listening = False
            try:
                if stream is not None:
                    stream.abort()
                    stream.close()
                    closed = True
            finally:
                # A broken driver's stream must not compete with a new stream.
                if closed:
                    MicrophoneCapture._owner.release()
