"""Push-to-talk coordinator. Only reviewed input enters the shared TaskService."""

import threading
import time
from pathlib import Path
from uuid import uuid4

from victus.voice.audio import resample_pcm16
from victus.voice.capture import MicrophoneCapture
from victus.voice.contracts import Transcript, VoiceSnapshot, VoiceState
from victus.voice.playback import Playback
from victus.voice.stt import TranscriptionWorker
from victus.voice.transcript_review import review_transcript


class VoiceConflict(RuntimeError):
    pass


class VoiceService:
    def __init__(
        self,
        tasks,
        model_path=None,
        *,
        capture_factory=MicrophoneCapture,
        transcriber=None,
        playback=None,
        review_seconds=120.0,
        result_seconds=180.0,
        commands=None,
    ):
        self.tasks = tasks
        from victus.tasks.commands import CommandService

        self.commands = commands or CommandService(tasks)
        self.wake = None
        self.capture_factory = capture_factory
        self.transcriber = transcriber or (
            TranscriptionWorker(str(model_path))
            if model_path and (Path(model_path) / "model.bin").is_file()
            else None
        )
        self.playback = playback or Playback()
        self.review_seconds, self.result_seconds = review_seconds, result_seconds
        self.lock = threading.RLock()
        self.cancelled = threading.Event()
        self.thread = None
        self.capture = None
        self.review_deadline = 0.0
        self.snapshot_value = VoiceSnapshot(
            enabled=self.transcriber is not None, state=VoiceState.IDLE
        )

    def _update(self, **changes):
        self.snapshot_value = self.snapshot_value.model_copy(
            update={**changes, "revision": self.snapshot_value.revision + 1}
        )

    def snapshot(self):
        with self.lock:
            if (
                self.snapshot_value.state in {VoiceState.REVIEWING, VoiceState.CLARIFYING}
                and time.monotonic() >= self.review_deadline
            ):
                self._cancel("TRANSCRIPT_REVIEW_EXPIRED")
            return self.snapshot_value.model_copy(
                update={
                    "muted": self.playback.muted,
                    "wake_suppressed": self.playback.wake_suppressed,
                    "wake_available": bool(self.wake and self.wake.available),
                    "wake_listening": bool(self.wake and self.wake.listening),
                    "wake_error": self.wake.error if self.wake else None,
                },
                deep=True,
            )

    def _require(self, session_id, revision, state):
        s = self.snapshot_value
        if (
            s.session_id != session_id
            or s.revision != revision
            or s.state != state
            or self.cancelled.is_set()
            or self.tasks.stopped.is_set()
        ):
            raise VoiceConflict("Voice state changed; refresh and review again")

    def start(self, *, from_wake=False, command_seconds=6.0):
        if self.wake is not None and not from_wake:
            self.wake.disable()  # Push to talk takes priority and requires explicit rearming.
        with self.lock:
            if not self.snapshot_value.enabled:
                raise VoiceConflict("Configure a downloaded local STT model first")
            if self.tasks.stopped.is_set():
                raise VoiceConflict("Restart the stopped service before recording")
            if self.snapshot_value.state not in {VoiceState.IDLE, VoiceState.ERROR} or (
                self.thread is not None and self.thread.is_alive()
            ):
                raise VoiceConflict("Finish or cancel the current voice session")
            if self.playback.wake_suppressed:
                raise VoiceConflict("Wait for speech playback and its echo cooldown to finish")
            self.cancelled = threading.Event()
            self.capture = (
                self.capture_factory(
                    max_seconds=command_seconds, initial_silence_seconds=min(4.0, command_seconds)
                )
                if from_wake
                else self.capture_factory()
            )
            self._update(
                state=VoiceState.RECORDING,
                session_id=uuid4().hex,
                transcript=None,
                proposal=None,
                clarification=None,
                error_code=None,
                task_id=None,
                summary=None,
                speech_pending=False,
                command=None,
            )
            self.thread = threading.Thread(
                target=self._run,
                args=(self.cancelled, self.capture),
                name="victus-voice",
                daemon=True,
            )
            self.thread.start()
            return self.snapshot()

    def finish(self, session_id, revision):
        with self.lock:
            self._require(session_id, revision, VoiceState.RECORDING)
            self.capture.finish()
            return self.snapshot()

    def _run(self, cancel, capture):
        pcm = b""
        try:
            if cancel.is_set():
                return
            if capture.done.is_set():
                raise RuntimeError("NO_SPEECH_DETECTED")
            capture.start()
            while not cancel.is_set() and not capture.done.wait(0.025):
                capture.check_limits()
                if self.tasks.stopped.is_set():
                    cancel.set()
            capture.close()
            if cancel.is_set():
                return
            if capture.error:
                raise RuntimeError(capture.error)
            if not capture.had_voice:
                raise RuntimeError("NO_SPEECH_DETECTED")
            pcm = resample_pcm16(capture.audio(), capture.sample_rate)
            capture.clear()
            with self.lock:
                if cancel.is_set():
                    return
                self._update(state=VoiceState.TRANSCRIBING)
            text = self.transcriber.transcribe(pcm, cancel)
            pcm = b""
            review = review_transcript(text)
            if not review.accepted:
                raise RuntimeError("NO_CLEAR_SPEECH")
            with self.lock:
                if cancel.is_set():
                    return
                self.review_deadline = time.monotonic() + self.review_seconds
                self._update(
                    state=VoiceState.REVIEWING,
                    transcript=Transcript(text=text),
                    proposal=review.action,
                    clarification=review.clarification,
                )
            del text, review
            while not cancel.wait(0.025):
                with self.lock:
                    if self.tasks.stopped.is_set():
                        self._cancel("VOICE_STOPPED")
                        return
                    if self.snapshot_value.state in {VoiceState.REVIEWING, VoiceState.CLARIFYING}:
                        if time.monotonic() >= self.review_deadline:
                            self._cancel("TRANSCRIPT_REVIEW_EXPIRED")
                            return
                        continue
                    task_id = self.snapshot_value.task_id
                    break
            if cancel.is_set():
                return
            deadline = time.monotonic() + self.result_seconds
            while not cancel.wait(0.05):
                task = self.tasks.database.get(task_id)
                if task and task.status not in {
                    "queued",
                    "prepared",
                    "running",
                    "waiting_for_review",
                }:
                    if task.status == "succeeded" and task.verified:
                        summary = "Your task completed with a verified output."
                    else:
                        summary = "The task ended without a verified output. Check the task result."
                    with self.lock:
                        if not cancel.is_set():
                            self._update(summary=summary, speech_pending=not self.playback.muted)
                    break
                if time.monotonic() >= deadline:
                    raise RuntimeError("VOICE_RESULT_DEADLINE_EXCEEDED")
            # Do not speak until the UI acknowledges this specific displayed revision.
            acknowledgement_deadline = time.monotonic() + 30
            while not cancel.wait(0.025):
                with self.lock:
                    s = self.snapshot_value
                    if s.state == VoiceState.SPEAKING and not self.playback.active:
                        if self.playback.error:
                            raise RuntimeError(self.playback.error)
                        self._update(state=VoiceState.SUBMITTED)
                        return
                    if not s.speech_pending and s.state != VoiceState.SPEAKING:
                        return
                    if time.monotonic() >= acknowledgement_deadline:
                        self._update(speech_pending=False)
                        return
        except Exception as error:
            with self.lock:
                if not cancel.is_set():
                    from victus.runtime.resources import ResourcePressure

                    code = str(error)
                    if isinstance(error, ResourcePressure):
                        code = "VOICE_RESOURCE_PRESSURE"
                    safe_codes = {
                        "MICROPHONE_BUSY",
                        "MICROPHONE_UNAVAILABLE",
                        "MICROPHONE_DISCONNECTED",
                        "AUDIO_INPUT_INTERRUPTED",
                        "INVALID_AUDIO_FRAME",
                        "NO_SPEECH_DETECTED",
                        "NO_CLEAR_SPEECH",
                        "STT_DEADLINE_EXCEEDED",
                        "STT_WORKER_EXITED",
                        "STT_MODEL_UNAVAILABLE",
                        "STT_FAILED",
                        "SPEECH_OUTPUT_UNAVAILABLE",
                        "VOICE_RESULT_DEADLINE_EXCEEDED",
                        "VOICE_RESOURCE_PRESSURE",
                    }
                    self._update(
                        state=VoiceState.ERROR,
                        error_code=code if code in safe_codes else "VOICE_FAILED",
                        transcript=None,
                        proposal=None,
                        speech_pending=False,
                    )
        finally:
            pcm = b""
            capture.close()
            capture.clear()

    def submit(self, session_id, revision, action):
        with self.lock:
            self._require(session_id, revision, VoiceState.REVIEWING)
            if time.monotonic() >= self.review_deadline:
                self._cancel("TRANSCRIPT_REVIEW_EXPIRED")
                raise VoiceConflict("Transcript review expired")
            # Only this explicit human-reviewed call can submit. No tool adapter calls here.
            from victus.agent.commands import CommandFields, CommandSubmission
            from victus.tools.contracts import ActionRequest

            if isinstance(action, ActionRequest):
                action = CommandSubmission(
                    text="Reviewed voice note",
                    fields=CommandFields(
                        intent="note",
                        filename=action.arguments.filename,
                        content=action.arguments.text,
                    ),
                )
            action = CommandSubmission.model_validate(action.model_dump(), strict=True)
            # Compare the server-held proposal, never client-supplied provenance.
            # Persist only a correction flag in the existing protected payload.
            from victus.agent.commands import interpret

            fields, missing = interpret(action)
            corrected = None
            if not missing and fields.intent == "note":
                reviewed = ActionRequest.model_validate(
                    {
                        "tool": "fs.create_note",
                        "arguments": {"filename": fields.filename, "text": fields.content},
                    }
                )
                corrected = reviewed != self.snapshot_value.proposal
            result = self.commands.submit(
                action, "voice-" + session_id, origin="voice", review_corrected=corrected
            )
            return self._command_result(result)

    def _command_result(self, result):
        task_id = result.task_id
        self._update(
            state=VoiceState.SUBMITTED if task_id else VoiceState.CLARIFYING,
            transcript=None,
            proposal=None,
            clarification=None,
            task_id=task_id,
            command=result,
        )
        return self.snapshot()

    def clarify(self, session_id, revision, fields):
        with self.lock:
            self._require(session_id, revision, VoiceState.CLARIFYING)
            if time.monotonic() >= self.review_deadline:
                self._cancel("TRANSCRIPT_REVIEW_EXPIRED")
                raise VoiceConflict("Transcript review expired")
            return self._command_result(
                self.commands.complete(self.snapshot_value.command.command_id, fields)
            )

    def acknowledge(self, session_id, revision):
        with self.lock:
            self._require(session_id, revision, VoiceState.SUBMITTED)
            s = self.snapshot_value
            if not s.speech_pending or not s.summary:
                raise VoiceConflict("No displayed summary is awaiting speech")
            if self.playback.play(s.summary):
                self._update(state=VoiceState.SPEAKING, speech_pending=False)
            else:
                self._update(speech_pending=False)
            return self.snapshot()

    def mute(self, value):
        with self.lock:
            self.playback.mute(value)
            self._update(speech_pending=False if value else self.snapshot_value.speech_pending)
            return self.snapshot()

    def _cancel(self, code=None):
        self.cancelled.set()
        if self.capture is not None:
            self.capture.finish()
        self.playback.interrupt()
        self._update(
            state=VoiceState.ERROR if code else VoiceState.IDLE,
            transcript=None,
            proposal=None,
            clarification=None,
            summary=None,
            speech_pending=False,
            error_code=code,
            command=None,
        )

    def cancel(self):
        with self.lock:
            self._cancel()
            return self.snapshot()

    def stop(self):
        self.cancelled.set()
        self.playback.interrupt()
        if self.wake is not None:
            self.wake.cancelled.set()
        with self.lock:
            self._cancel("VOICE_STOPPED")

    def device_disconnected(self):
        self.cancelled.set()
        self.playback.interrupt()
        with self.lock:
            self._cancel("MICROPHONE_DISCONNECTED")

    def close(self):
        if self.wake is not None:
            self.wake.disable()
        self.cancel()
        if self.thread is not None:
            self.thread.join(timeout=5)
            if self.thread.is_alive():
                raise RuntimeError("VOICE_SHUTDOWN_FAILED")
        self.playback.close()
        if self.transcriber is not None:
            self.transcriber.close()
