"""One interruptible output owner; wake detection is suppressed through echo cooldown."""

import threading
import time

from victus.voice.tts import SapiSpeechOutput


class Playback:
    def __init__(self, output=None, *, timeout=20.0, cooldown=0.75):
        self.output = output or SapiSpeechOutput()
        self.timeout, self.cooldown = timeout, cooldown
        self.muted = False
        self.interrupted = threading.Event()
        self.lock = threading.RLock()
        self.thread = None
        self.active = False
        self.quiet_until = 0.0
        self.error = None

    @property
    def wake_suppressed(self):
        with self.lock:
            return self.active or time.monotonic() < self.quiet_until

    def play(self, text):
        with self.lock:
            if self.muted or self.active:
                return False
            self.interrupted = threading.Event()
            self.error = None
            self.active = True
            self.thread = threading.Thread(
                target=self._speak, args=(text, self.interrupted), name="victus-speech", daemon=True
            )
            self.thread.start()
            return True

    def _speak(self, text, signal):
        try:
            self.output.speak(text, signal, time.monotonic() + self.timeout)
        except Exception:
            self.error = "SPEECH_OUTPUT_UNAVAILABLE"
        finally:
            with self.lock:
                self.active = False
                self.quiet_until = time.monotonic() + self.cooldown

    def interrupt(self):
        with self.lock:
            self.interrupted.set()

    def mute(self, value):
        with self.lock:
            self.muted = value
            if value:
                self.interrupted.set()

    def close(self):
        self.interrupt()
        if self.thread is not None:
            self.thread.join(timeout=2)
            if self.thread.is_alive():
                raise RuntimeError("SPEECH_SHUTDOWN_FAILED")
