"""Offline Whisper adapter and a persistent, killable inference worker."""

import multiprocessing
import threading
import time
from pathlib import Path

from victus.runtime.resources import resources


class LocalTranscriber:
    def __init__(self, model_path: str):
        path = Path(model_path).expanduser().resolve(strict=True)
        if not path.is_dir() or not (path / "model.bin").is_file():
            raise ValueError("A downloaded CTranslate2 model directory is required")
        from faster_whisper import WhisperModel

        self.model = WhisperModel(
            str(path),
            device="cpu",
            compute_type="int8",
            local_files_only=True,
            cpu_threads=4,
            num_workers=1,
        )

    def transcribe(self, audio_path: str) -> str:
        return self._consume(audio_path)

    def transcribe_pcm(self, pcm: bytes) -> str:
        import numpy as np

        # The worker receives 16 kHz mono PCM; no temporary audio file is created.
        audio = np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768
        return self._consume(audio)

    def _consume(self, audio) -> str:
        segments, _ = self.model.transcribe(
            audio, vad_filter=True, language="en", condition_on_previous_text=False
        )
        # Iteration is inference, not merely a string formatting step.
        text = " ".join(segment.text.strip() for segment in segments).strip()
        if len(text) > 8192:
            raise ValueError("Transcript limit exceeded")
        return text


def _inference_worker(connection, model_path):
    try:
        transcriber = LocalTranscriber(model_path)
        connection.send(("ready", None))
        while True:
            pcm = connection.recv()
            if pcm is None:
                break
            try:
                text = transcriber.transcribe_pcm(pcm)
                connection.send(("result", text))
                del text
            finally:
                del pcm
    except (EOFError, BrokenPipeError):
        pass
    except Exception:
        # Do not leak transcripts, paths, device names or third-party tracebacks.
        try:
            connection.send(("error", None))
        except (EOFError, BrokenPipeError, OSError):
            pass
    finally:
        connection.close()


class TranscriptionWorker:
    def __init__(self, model_path: str, *, timeout=90.0, target=_inference_worker):
        self.model_path = model_path
        self.timeout = timeout
        self.target = target
        self.context = multiprocessing.get_context("spawn")
        self.process = self.connection = None
        self.lock = threading.Lock()
        self.loaded = False

    def _receive(self, cancel, deadline):
        while time.monotonic() < deadline:
            if cancel.is_set():
                raise RuntimeError("VOICE_CANCELLED")
            if self.connection.poll(0.05):
                try:
                    return self.connection.recv()
                except (EOFError, OSError):
                    raise RuntimeError("STT_WORKER_EXITED") from None
            if not self.process.is_alive():
                raise RuntimeError("STT_WORKER_EXITED")
        raise RuntimeError("STT_DEADLINE_EXCEEDED")

    def transcribe(self, pcm: bytes, cancel: threading.Event) -> str:
        deadline = time.monotonic() + self.timeout
        with resources().inference_slot("stt", cancel, timeout=self.timeout, warm=self.loaded):
            return self._transcribe(pcm, cancel, deadline)

    def _transcribe(self, pcm, cancel, deadline):
        with self.lock:
            try:
                if cancel.is_set():
                    raise RuntimeError("VOICE_CANCELLED")
                if self.process is None:
                    parent, child = self.context.Pipe()
                    self.connection = parent
                    self.process = self.context.Process(
                        target=self.target, args=(child, self.model_path), daemon=True
                    )
                    try:
                        self.process.start()
                    finally:
                        child.close()
                    kind, _ = self._receive(cancel, deadline)
                    if kind != "ready":
                        raise RuntimeError("STT_MODEL_UNAVAILABLE")
                    self.loaded = True
                sent = threading.Event()
                send_failed = threading.Event()
                connection = self.connection

                def send_audio():
                    try:
                        connection.send(pcm)
                    except (OSError, EOFError):
                        send_failed.set()
                    finally:
                        sent.set()

                sender = threading.Thread(target=send_audio, name="victus-audio-ipc", daemon=True)
                sender.start()
                while not sent.wait(0.025):
                    if cancel.is_set():
                        raise RuntimeError("VOICE_CANCELLED")
                    if time.monotonic() >= deadline:
                        raise RuntimeError("STT_DEADLINE_EXCEEDED")
                if send_failed.is_set():
                    raise RuntimeError("STT_WORKER_EXITED")
                kind, text = self._receive(cancel, deadline)
                if kind != "result" or not isinstance(text, str) or len(text) > 8192:
                    raise RuntimeError("STT_FAILED")
                return text
            except Exception:
                self._terminate()
                raise

    def _terminate(self):
        if self.process is not None:
            if self.process.pid is not None:
                self.process.terminate()
                self.process.join(timeout=2)
                if self.process.is_alive():
                    self.process.kill()
                    self.process.join(timeout=1)
                if self.process.is_alive():
                    raise RuntimeError("STT_SHUTDOWN_FAILED")
            self.process.close()
        if self.connection is not None:
            self.connection.close()
        self.process = self.connection = None
        self.loaded = False

    def close(self):
        # Caller first cancels/joins the voice coordinator, then closes inference.
        with self.lock:
            self._terminate()
