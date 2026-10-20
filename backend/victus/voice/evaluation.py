"""Labelled English-only M6 evaluation. Metrics are distinct from permission.

No microphone recording, task submission, model download or raw transcript logging.
"""

import argparse
import json
import re
import threading
import wave
from collections import Counter
from pathlib import Path

from victus.voice.audio import resample_pcm16
from victus.voice.model_assets import model_identity
from victus.voice.stt import TranscriptionWorker
from victus.voice.transcript_review import review_transcript
from victus.workflows.qualification_records import file_hash, runtime_identity


def words(text):
    return re.findall(r"[\w]+", text.casefold())


def word_errors(reference, hypothesis):
    expected, actual = words(reference), words(hypothesis)
    previous = list(range(len(actual) + 1))
    for i, left in enumerate(expected, 1):
        current = [i]
        for j, right in enumerate(actual, 1):
            current.append(min(current[-1] + 1, previous[j] + 1, previous[j - 1] + (left != right)))
        previous = current
    return previous[-1], len(expected)


def score(rows):
    groups = {}
    for row in rows:
        group = groups.setdefault(
            row["condition"],
            {
                "samples": 0,
                "word_errors": 0,
                "reference_words": 0,
                "intent_correct": 0,
                "target_correct": 0,
                "non_command_with_proposal": 0,
            },
        )
        group["samples"] += 1
        for key in (
            "word_errors",
            "reference_words",
            "intent_correct",
            "target_correct",
            "non_command_with_proposal",
        ):
            group[key] += row[key]
    for group in groups.values():
        group["word_error_rate"] = (
            group["word_errors"] / group["reference_words"] if group["reference_words"] else None
        )
        group["intent_accuracy"] = group["intent_correct"] / group["samples"]
        group["target_accuracy"] = group["target_correct"] / group["samples"]
    return groups


def evaluate(manifest, worker):
    source_before = runtime_identity()
    manifest_before = file_hash(manifest)
    labels = json.loads(manifest.read_text(encoding="utf-8"))
    if not isinstance(labels, list) or len(labels) > 1000:
        raise ValueError("Expected a bounded JSON array of labelled samples")
    counts = Counter(item["condition"] for item in labels)
    if counts["quiet"] != 50 or counts["noisy"] != 50:
        raise ValueError("Supply exactly 50 quiet and 50 noisy labelled commands")
    if any(not counts[name] for name in ("silence", "background", "assistant_speech")):
        raise ValueError("Include silence, background and assistant_speech negative samples")
    if worker is None or getattr(worker, "loaded", False):
        raise ValueError("Use a fresh transcription worker bound to local STT assets")
    asset_before = model_identity(worker.model_path)
    identifiers = set()
    audio_hashes = set()
    rows = []
    for item in labels:
        sample_id = item["id"]
        if not isinstance(sample_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", sample_id):
            raise ValueError("Use opaque sample identifiers")
        if sample_id in identifiers:
            raise ValueError("Duplicate sample identifier")
        identifiers.add(sample_id)
        if item.get("language") != "en":
            raise ValueError("This test set only qualifies English; supply separate language sets")
        audio_path = (manifest.parent / item["audio"]).resolve(strict=True)
        audio_digest = file_hash(audio_path)
        if audio_digest in audio_hashes:
            raise ValueError("Each recording must be distinct")
        audio_hashes.add(audio_digest)
        with wave.open(str(audio_path), "rb") as audio:
            if (
                audio.getsampwidth() != 2
                or audio.getnchannels() not in (1, 2)
                or not 8000 <= audio.getframerate() <= 48000
                or audio.getnframes() > 30 * audio.getframerate()
            ):
                raise ValueError("Expected <=30 second PCM16 mono/stereo WAV")
            pcm = resample_pcm16(
                audio.readframes(audio.getnframes()),
                audio.getframerate(),
                channels=audio.getnchannels(),
            )
        transcript = worker.transcribe(pcm, threading.Event())
        review = review_transcript(transcript)
        intent = "fs.create_note" if re.match(r"^\s*create note\b", transcript, re.I) else None
        target = review.action.arguments.filename if review.action else None
        errors, reference_words = word_errors(item["reference"], transcript)
        rows.append(
            {
                "id": sample_id,
                "audio_sha256": audio_digest,
                "condition": item["condition"],
                "word_errors": errors,
                "reference_words": reference_words,
                "intent_correct": int(intent == item["intent"]),
                "target_correct": int(target == item["target"]),
                "non_command_with_proposal": int(
                    item["intent"] is None and review.action is not None
                ),
            }
        )
        if file_hash(audio_path) != audio_digest:
            raise ValueError("Recording changed during evaluation")
        del pcm, transcript
    if (
        file_hash(manifest) != manifest_before
        or runtime_identity() != source_before
        or model_identity(worker.model_path) != asset_before
    ):
        raise ValueError("Evaluation inputs changed")
    return {
        "runtime_sha256": source_before,
        "runtime_end_sha256": runtime_identity(),
        "manifest_sha256": manifest_before,
        "stt_model_sha256": asset_before,
        "language": "en",
        "groups": score(rows),
        "samples": rows,
        "automatic_submission": "disabled_by_design_requires_explicit_review",
        "physical_disconnect_and_echo_qualification": "requires_separate_observed_test",
        "hindi_or_mixed_language_qualified": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    worker = TranscriptionWorker(str(args.model.resolve(strict=True)))
    try:
        report = evaluate(args.manifest.resolve(strict=True), worker)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(report, indent=2) + "\n")
    finally:
        worker.close()


if __name__ == "__main__":
    main()
