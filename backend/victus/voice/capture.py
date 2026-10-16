"""One Python microphone stream with bounded retention and finite energy VAD.

Energy gating detects activity, not speaker identity or speech semantics.
"""

import threading
import time
from collections import deque

from victus.voice.audio import rms
from victus.voice.contracts import AudioFrame


class MicrophoneCapture:
    _owner = threading.Lock()

    def __init__(
        self,
        *,
        sample_rate=16000,
        max_seconds=20.0,
        silence_seconds=1.5,
        initial_silence_seconds=4.0,
        threshold=0.012,
        stream_factory=None,
        clock=time.monotonic,
    ):
        if not (
            8000 <= sample_rate <= 48000
            and 0 < silence_seconds <= max_seconds <= 30
            and 0 < initial_silence_seconds <= max_seconds
            and 0 < threshold < 1
        ):
            raise ValueError("Invalid capture limits")
        self.sample_rate, self.max_seconds = sample_rate, max_seconds
        self.silence_seconds, self.initial_silence_seconds = (
            silence_seconds,
            initial_silence_seconds,
        )
        self.threshold, self.factory, self.clock = threshold, stream_factory, clock
        self.max_bytes = int(sample_rate * max_seconds) * 2
        self.frames = deque()
        self.size = 0
        self.lock = threading.Lock()
        self.done = threading.Event()
        self.error = None
        self.stream = None
        self.owned = False
        self.started_at = self.last_voice = 0.0
        self.had_voice = False
        self.sequence = 0

    def start(self):
        if self.done.is_set():
            raise RuntimeError("VOICE_CANCELLED")
        if not self._owner.acquire(blocking=False):
            raise RuntimeError("MICROPHONE_BUSY")
        self.owned = True
        self.started_at = self.last_voice = self.clock()
        try:
            factory = self.factory
            if factory is None:
                from sounddevice import RawInputStream

                factory = RawInputStream
            self.stream = factory(
                samplerate=self.sample_rate,
                channels=1,
                dtype="int16",
                blocksize=int(self.sample_rate * 0.02),
                callback=self._callback,
            )
            if self.done.is_set():
                self.close()
                return
            self.stream.start()
        except Exception:
            self.close()
            raise RuntimeError("MICROPHONE_UNAVAILABLE") from None

    def _callback(self, data, _frames, _timing, status):
        if self.done.is_set():
            return
        if status:
            self.error = "AUDIO_INPUT_INTERRUPTED"
            self.done.set()
            return
        raw = bytes(data)
        if not raw or len(raw) != _frames * 2 or len(raw) % 2 or len(raw) > self.max_bytes:
            self.error = "INVALID_AUDIO_FRAME"
            self.done.set()
            return
        now = self.clock()
        with self.lock:
            while self.frames and self.size + len(raw) > self.max_bytes:
                self.size -= len(self.frames.popleft().pcm)
            self.frames.append(
                AudioFrame(self.sequence, now, self.sample_rate, 1, "pcm_s16le", raw)
            )
            self.sequence += 1
            self.size += len(raw)
        if rms(raw) >= self.threshold:
            self.had_voice = True
            self.last_voice = now
        self.check_limits()

    def check_limits(self):
        now = self.clock()
        if now - self.started_at >= self.max_seconds:
            self.done.set()
        elif self.had_voice and now - self.last_voice >= self.silence_seconds:
            self.done.set()
        elif not self.had_voice and now - self.started_at >= self.initial_silence_seconds:
            self.done.set()
        try:
            disconnected = self.stream is not None and not self.stream.active
        except Exception:
            disconnected = True
        if disconnected:
            self.error = "MICROPHONE_DISCONNECTED"
            self.done.set()

    def finish(self):
        self.done.set()

    def audio(self):
        with self.lock:
            return b"".join(frame.pcm for frame in self.frames)

    def clear(self):
        with self.lock:
            self.frames.clear()
            self.size = 0

    def close(self):
        if self.stream is not None:
            try:
                self.stream.abort()
            except Exception:
                pass
            try:
                self.stream.close()
            except Exception:
                # Retain the global owner if the driver did not confirm closure.
                # Another capture must never compete with this stream.
                self.error = "MICROPHONE_DISCONNECTED"
                return
            self.stream = None
        if self.owned:
            self.owned = False
            self._owner.release()
