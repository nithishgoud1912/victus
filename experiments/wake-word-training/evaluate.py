"""Evaluate consented, held-out WAVs offline. Never records or downloads audio.

Usage: python experiments/wake-word-training/evaluate.py CONFIG CORPUS OUTPUT
CONFIG: WakeConfiguration JSON; CORPUS: list of {path,sha256,label,provenance}.
Each label is positive or realistic_negative. Every clip must be unique, mono
16 kHz PCM16. The result needs human review before being used as a manifest.
"""

import hashlib
import json
import sys
import wave
from pathlib import Path

from victus.voice.wake import OpenWakeWordDetector, WakeConfiguration


def evaluate(config, clips):
    detector = OpenWakeWordDetector(config)
    seen = set()
    positives = hits = false_activations = 0
    negative_seconds = 0.0
    if not isinstance(clips, list) or len(clips) > 10000:
        raise ValueError("Invalid corpus")
    for clip in clips:
        path = Path(clip["path"]).resolve(strict=True)
        if any((p / ".git").exists() for p in path.parents):
            raise ValueError("Keep audio outside Git")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != clip["sha256"] or digest in seen or not clip["provenance"]:
            raise ValueError("Unique checksummed clips and provenance required")
        seen.add(digest)
        label = clip["label"]
        if label not in {"positive", "realistic_negative"}:
            raise ValueError("Unsupported label")
        detector.reset()
        detected = 0
        next_allowed = 0.0
        with wave.open(str(path), "rb") as audio:
            if (audio.getnchannels(), audio.getsampwidth(), audio.getframerate()) != (1, 2, 16000):
                raise ValueError("Expected mono 16 kHz PCM16 WAV")
            duration = audio.getnframes() / 16000
            if duration <= 0:
                raise ValueError("Empty audio cannot qualify a model")
            offset = 0.0
            while pcm := audio.readframes(1280):
                if len(pcm) < 2560:
                    pcm += b"\0" * (2560 - len(pcm))
                if detector.score(pcm) >= config.threshold and offset >= next_allowed:
                    detected += 1
                    next_allowed = offset + config.cooldown_seconds
                offset += 0.08
        if label == "positive":
            positives += 1
            hits += int(detected > 0)
        else:
            negative_seconds += duration
            false_activations += detected
    return {
        "configuration": config.model_dump(),
        "qualification": {
            "configuration_sha256": config.identity(),
            "corpus_sha256": hashlib.sha256(json.dumps(clips, sort_keys=True).encode()).hexdigest(),
            "positive_clips": positives,
            "positive_recall": hits / positives if positives else 0.0,
            "negative_seconds": negative_seconds,
            "false_activations_per_hour": false_activations * 3600 / negative_seconds
            if negative_seconds else 0.0,
            "realistic_negative_audio": True,
            "human_reviewed": False,
        },
    }


if __name__ == "__main__":
    config = WakeConfiguration.model_validate_json(Path(sys.argv[1]).read_text())
    result = evaluate(config, json.loads(Path(sys.argv[2]).read_text()))
    Path(sys.argv[3]).write_text(json.dumps(result, indent=2) + "\n")
