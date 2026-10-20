"""Predeclared English-note voice protocol and read-only result aggregation.

No capture, inference or task execution is performed by this module. Real audio,
reviewed command pairing and witnessed physical observations remain necessary.
"""

import argparse
import hashlib
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path

from victus.voice.model_assets import model_identity
from victus.workflows.qualification_records import file_hash, read_record, runtime_identity

PHYSICAL_CHECKS = frozenset(
    {
        "unplug_reconnect",
        "stop_spoken_decoding",
        "stop_review",
        "stop_playback",
        "audible_mute_interrupt",
        "speaker_echo_cooldown",
        "physical_emergency_shortcut",
    }
)
METRICS = {
    "max_word_error_rate",
    "min_intent_accuracy",
    "min_target_accuracy",
    "min_action_accuracy",
}


def _write(path, value):
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2) + "\n")


def _validate_limits(limits):
    if set(limits) != {"quiet", "noisy", "max_negative_proposals"}:
        raise ValueError("Predeclare both condition thresholds and negative proposal limit")
    for condition in ("quiet", "noisy"):
        if not isinstance(limits[condition], dict) or set(limits[condition]) != METRICS:
            raise ValueError("All condition thresholds required")
        for value in limits[condition].values():
            if type(value) not in {int, float} or not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError("Thresholds must be finite fractions from zero to one")
    if type(limits["max_negative_proposals"]) is not int or limits["max_negative_proposals"] < 0:
        raise ValueError("Nonnegative negative-proposal limit required")


def _mapping(value):
    return value if isinstance(value, dict) else {}


def prepare(manifest, thresholds, output, *, model=None):
    raw = Path(manifest).read_bytes()
    labels = json.loads(raw)
    if (
        not isinstance(labels, list)
        or len(labels) > 1000
        or any(not isinstance(row, dict) for row in labels)
        or sum(r.get("condition") == "quiet" for r in labels) != 50
        or sum(r.get("condition") == "noisy" for r in labels) != 50
        or len({row["id"] for row in labels}) != len(labels)
        or any(row.get("language") != "en" for row in labels)
        or not {"silence", "background", "assistant_speech"} <= {r.get("condition") for r in labels}
    ):
        raise ValueError("Exactly 50 quiet/50 noisy English labels plus negatives required")
    limits, _ = read_record(thresholds)
    _validate_limits(limits)
    assets = model_identity(model) if model is not None else None
    output = Path(output).absolute()
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    (output / "manifest.json").write_bytes(raw)
    _write(
        output / "physical.json",
        {
            "runtime_sha256": runtime_identity(),
            "runtime_end_sha256": None,
            "human_witnessed": False,
            "stt_model_sha256": assets,
            "checks": dict.fromkeys(sorted(PHYSICAL_CHECKS), False),
        },
    )
    protocol = {
        "schema_version": 2,
        "kind": "english_note_voice",
        "prepared_at": datetime.now(timezone.utc).isoformat(),
        "runtime_sha256": runtime_identity(),
        "manifest_sha256": hashlib.sha256(raw).hexdigest(),
        "stt_model_sha256": assets,
        "thresholds": limits,
        "qualification": "pending_real_recordings_and_observations",
    }
    _write(output / "protocol.json", protocol)
    return output / "protocol.json"


def evaluate(protocol_file, output):
    protocol_file = Path(protocol_file).absolute()
    protocol, protocol_hash = read_record(protocol_file)
    root = protocol_file.parent
    if (
        protocol.get("kind") != "english_note_voice"
        or protocol.get("runtime_sha256") != runtime_identity()
        or file_hash(root / "manifest.json") != protocol.get("manifest_sha256")
    ):
        raise ValueError("Unchanged predeclared protocol and manifest required")
    _validate_limits(protocol["thresholds"])
    checks, missing, references = {}, [], {}
    reports = {}
    for key in ("recognition", "actions", "physical"):
        path = root / (key + ".json")
        try:
            reports[key], references[key] = read_record(path)
        except (OSError, ValueError):
            missing.append(key)
    recognition, actions, physical = (
        reports.get(key, {}) for key in ("recognition", "actions", "physical")
    )
    identities = all(
        report.get("manifest_sha256") == protocol["manifest_sha256"]
        and report.get("runtime_sha256") == runtime_identity()
        and report.get("runtime_end_sha256") == runtime_identity()
        for report in (recognition, actions)
    )
    checks["matching_report_identities"] = identities
    assets = protocol.get("stt_model_sha256")
    checks["stt_asset_identity"] = (
        isinstance(assets, str)
        and re.fullmatch(r"[a-f0-9]{64}", assets) is not None
        and recognition.get("stt_model_sha256") == assets
    )
    corrections_complete = True
    for condition in ("quiet", "noisy"):
        r = _mapping(_mapping(recognition.get("groups")).get(condition))
        a = _mapping(_mapping(actions.get("groups")).get(condition))
        limits = protocol["thresholds"][condition]
        values = {
            "max_word_error_rate": r.get("word_error_rate"),
            "min_intent_accuracy": r.get("intent_accuracy"),
            "min_target_accuracy": r.get("target_accuracy"),
            "min_action_accuracy": a.get("accuracy"),
        }
        valid = (
            all(type(v) is int for v in (r.get("samples"), a.get("measured"), a.get("unmeasured")))
            and r.get("samples") == 50
            and a.get("measured") == 50
            and a.get("unmeasured") == 0
        )
        for name, value in values.items():
            valid = (
                valid
                and type(value) in {int, float}
                and math.isfinite(value)
                and value >= 0
                and (name == "max_word_error_rate" or value <= 1)
                and (value <= limits[name] if name.startswith("max_") else value >= limits[name])
            )
        checks[condition] = bool(valid)
        count, corrected, rate = (
            a.get(key) for key in ("corrections_measured", "corrected_reviews", "correction_rate")
        )
        corrections_complete = corrections_complete and (
            type(count) is int
            and count == 50
            and type(corrected) is int
            and 0 <= corrected <= count
            and type(rate) in {int, float}
            and math.isfinite(rate)
            and abs(rate - corrected / count) < 1e-9
        )
    checks["review_corrections_reported"] = bool(corrections_complete)
    negatives = [
        _mapping(recognition.get("groups")).get(key)
        for key in ("silence", "background", "assistant_speech")
    ]
    valid_negatives = all(
        isinstance(row, dict)
        and type(row.get("samples")) is int
        and row["samples"] > 0
        and type(row.get("non_command_with_proposal")) is int
        and 0 <= row["non_command_with_proposal"] <= row["samples"]
        for row in negatives
    )
    checks["negatives"] = (
        valid_negatives
        and sum(row["non_command_with_proposal"] for row in negatives)
        <= protocol["thresholds"]["max_negative_proposals"]
    )
    checks["physical"] = (
        physical.get("human_witnessed") is True
        and physical.get("stt_model_sha256") == assets
        and assets is not None
        and physical.get("runtime_sha256") == runtime_identity()
        and physical.get("runtime_end_sha256") == runtime_identity()
        and all(_mapping(physical.get("checks")).get(key) is True for key in PHYSICAL_CHECKS)
    )
    report = {
        "schema_version": 2,
        "runtime_sha256": runtime_identity(),
        "protocol_sha256": protocol_hash,
        "references_sha256": references,
        "checks": checks,
        "missing": missing,
        "qualified": not missing and all(checks.values()),
        "operator_pairing_and_witness_limitations": True,
        "recognition_and_corrected_actions_are_separate": True,
    }
    _write(Path(output), report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "evaluate"])
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--thresholds", type=Path)
    parser.add_argument(
        "--model", type=Path, help="Explicit local STT assets; absent stays unqualified"
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        if args.thresholds is None:
            parser.error("prepare requires predeclared --thresholds")
        print(prepare(args.source, args.thresholds, args.output, model=args.model))
    else:
        report = evaluate(args.source, args.output)
        raise SystemExit(0 if report["qualified"] else 2)


if __name__ == "__main__":
    main()
