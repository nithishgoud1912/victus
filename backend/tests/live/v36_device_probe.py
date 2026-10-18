"""Bounded real-device probe; audio discarded, no acoustic-accuracy or unplug claim."""

import argparse
import hashlib
import json
import secrets
import threading
import time
from pathlib import Path

from victus.voice.capture import MicrophoneCapture
from victus.voice.playback import Playback
from victus.voice.stt import TranscriptionWorker


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    report = {
        "physical_microphone_opened": False,
        "raw_audio_saved": False,
        "private_speech_spoken": False,
        "quiet_commands_measured": 0,
        "noisy_commands_measured": 0,
        "unplug_reconnect_observed": False,
        "real_speaker_echo_measured": False,
        "audibility_observed_by_human": False,
        "checks": {},
        "errors": {},
    }
    first = MicrophoneCapture(max_seconds=2, initial_silence_seconds=2)
    second = MicrophoneCapture(max_seconds=2, initial_silence_seconds=2)
    try:
        first.start()
        report["physical_microphone_opened"] = True
        try:
            second.start()
            report["checks"]["microphone_single_owner"] = False
        except RuntimeError as error:
            report["checks"]["microphone_single_owner"] = str(error) == "MICROPHONE_BUSY"
        time.sleep(0.5)
        first.finish()
        first.close()
        report["checks"]["microphone_cancel_closes_owner"] = not first.owned
        first.clear()
        second.start()
        second.finish()
        second.close()
        report["checks"]["microphone_reacquired_after_close"] = not second.owned
    except Exception as error:
        report["errors"]["microphone"] = (
            str(error)
            if str(error) in {"MICROPHONE_UNAVAILABLE", "MICROPHONE_BUSY"}
            else type(error).__name__
        )
    finally:
        first.finish()
        second.finish()
        first.close()
        second.close()
        first.clear()
        second.clear()
    playback = Playback(timeout=3)
    try:
        playback.play("The device check has finished.")
        report["checks"]["playback_suppression_latched"] = playback.wake_suppressed
        time.sleep(0.25)
        playback.interrupt()
        playback.close()
        report["checks"]["sapi_interrupt_completed"] = (
            playback.error is None and not playback.active
        )
        report["checks"]["playback_cooldown_suppresses_capture"] = playback.wake_suppressed
    except Exception as error:
        report["errors"]["sapi"] = type(error).__name__
    finally:
        playback.close()
    if args.model:
        from fastapi.testclient import TestClient

        from victus.api.app import create_app
        from victus.settings import Settings

        token = secrets.token_urlsafe(48)
        headers = {"Authorization": "Bearer " + token}
        with TestClient(
            create_app(
                Settings(
                    data_dir=args.output / "stop-runtime",
                    api_token=token,
                    voice_model_path=args.model,
                )
            ),
            base_url="http://127.0.0.1",
        ) as client:
            response = client.post("/api/voice/start", headers=headers)
            voice = client.app.state.services.voice
            deadline = time.monotonic() + 3
            while (
                voice.capture is not None
                and not voice.capture.owned
                and voice.thread.is_alive()
                and time.monotonic() < deadline
            ):
                time.sleep(0.01)
            owned = bool(voice.capture and voice.capture.owned)
            client.post("/api/stop", headers=headers)
            if voice.thread:
                voice.thread.join(timeout=5)
            report["checks"]["http_stop_closes_real_microphone"] = (
                response.status_code == 200
                and owned
                and not voice.thread.is_alive()
                and not voice.capture.owned
                and voice.capture.size == 0
                and voice.snapshot().error_code == "VOICE_STOPPED"
                and voice.snapshot().transcript is None
            )
        worker = TranscriptionWorker(str(args.model.resolve(strict=True)))
        cancel = threading.Event()
        outcomes = []

        def transcribe():
            try:
                worker.transcribe(b"\0" * 32000, cancel)
                outcomes.append("completed")
            except Exception as error:
                outcomes.append(
                    str(error)
                    if str(error) in {"VOICE_CANCELLED", "STT_DEADLINE_EXCEEDED"}
                    else type(error).__name__
                )

        thread = threading.Thread(target=transcribe, daemon=True)
        thread.start()
        deadline = time.monotonic() + 5
        while worker.process is None and thread.is_alive() and time.monotonic() < deadline:
            time.sleep(0.01)
        started = worker.process is not None
        cancel.set()
        thread.join(timeout=5)
        report["checks"]["local_stt_worker_cancelled"] = (
            started
            and not thread.is_alive()
            and worker.process is None
            and outcomes == ["VOICE_CANCELLED"]
        )
        report["stt_outcome"] = outcomes
        worker.close()
        with (args.model / "model.bin").open("rb") as model_file:
            report["model_sha256"] = hashlib.file_digest(model_file, "sha256").hexdigest()
    report["release_qualified"] = False
    (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
