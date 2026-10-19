"""Predeclared English-note voice protocol and read-only result aggregation.

No capture, inference or task execution is performed by this module. Real audio,
reviewed command pairing and witnessed physical observations remain necessary.
"""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from victus.workflows.qualification_records import file_hash, read_record, runtime_identity

PHYSICAL_CHECKS = frozenset({"unplug_reconnect", "stop_spoken_decoding", "stop_review",
                             "stop_playback", "audible_mute_interrupt", "speaker_echo_cooldown",
                             "physical_emergency_shortcut"})
METRICS = {"max_word_error_rate", "min_intent_accuracy", "min_target_accuracy", "min_action_accuracy"}


def _write(path, value):
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2) + "\n")


def prepare(manifest, thresholds, output):
    raw = Path(manifest).read_bytes()
    labels = json.loads(raw)
    if (not isinstance(labels, list) or len(labels) > 1000
            or sum(r.get("condition") == "quiet" for r in labels) != 50
            or sum(r.get("condition") == "noisy" for r in labels) != 50
            or len({row["id"] for row in labels}) != len(labels)
            or any(row.get("language") != "en" for row in labels)
            or not {"silence", "background", "assistant_speech"} <= {r.get("condition") for r in labels}):
        raise ValueError("Exactly 50 quiet/50 noisy English labels plus negatives required")
    limits, _ = read_record(thresholds)
    if set(limits) != {"quiet", "noisy", "max_negative_proposals"}:
        raise ValueError("Predeclare both condition thresholds and negative proposal limit")
    for condition in ("quiet", "noisy"):
        if not isinstance(limits[condition], dict) or set(limits[condition]) != METRICS:
            raise ValueError("All condition thresholds required")
        for value in limits[condition].values():
            if type(value) not in {int, float} or not 0 <= value <= 1:
                raise ValueError("Thresholds must be finite fractions from zero to one")
    if type(limits["max_negative_proposals"]) is not int or limits["max_negative_proposals"] < 0:
        raise ValueError("Nonnegative negative-proposal limit required")
    output = Path(output).absolute()
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    (output / "manifest.json").write_bytes(raw)
    _write(output / "physical.json", {"runtime_sha256": runtime_identity(),
           "runtime_end_sha256": None, "human_witnessed": False,
           "checks": dict.fromkeys(sorted(PHYSICAL_CHECKS), False)})
    protocol = {"schema_version": 1, "kind": "english_note_voice",
                "prepared_at": datetime.now(timezone.utc).isoformat(),
                "runtime_sha256": runtime_identity(), "manifest_sha256": hashlib.sha256(raw).hexdigest(),
                "thresholds": limits, "qualification": "pending_real_recordings_and_observations"}
    _write(output / "protocol.json", protocol)
    return output / "protocol.json"


def evaluate(protocol_file, output):
    protocol_file = Path(protocol_file).absolute()
    protocol, protocol_hash = read_record(protocol_file)
    root = protocol_file.parent
    if (protocol.get("kind") != "english_note_voice" or protocol.get("runtime_sha256") != runtime_identity()
            or file_hash(root / "manifest.json") != protocol.get("manifest_sha256")):
        raise ValueError("Unchanged predeclared protocol and manifest required")
    checks, missing, references = {}, [], {}
    reports = {}
    for key in ("recognition", "actions", "physical"):
        path = root / (key + ".json")
        try:
            reports[key], references[key] = read_record(path)
        except (OSError, ValueError):
            missing.append(key)
    recognition, actions, physical = (reports.get(key, {}) for key in ("recognition", "actions", "physical"))
    identities = all(report.get("manifest_sha256") == protocol["manifest_sha256"]
                     and report.get("runtime_sha256") == runtime_identity()
                     and report.get("runtime_end_sha256") == runtime_identity()
                     for report in (recognition, actions))
    checks["matching_report_identities"] = identities
    for condition in ("quiet", "noisy"):
        r = recognition.get("groups", {}).get(condition, {})
        a = actions.get("groups", {}).get(condition, {})
        limits = protocol["thresholds"][condition]
        values = {"max_word_error_rate": r.get("word_error_rate"),
                  "min_intent_accuracy": r.get("intent_accuracy"),
                  "min_target_accuracy": r.get("target_accuracy"),
                  "min_action_accuracy": a.get("accuracy")}
        valid = r.get("samples") == 50 and a.get("measured") == 50 and a.get("unmeasured") == 0
        for name, value in values.items():
            valid = valid and type(value) in {int, float} and (
                value <= limits[name] if name.startswith("max_") else value >= limits[name])
        checks[condition] = bool(valid)
    negatives = [recognition.get("groups", {}).get(key) for key in ("silence", "background", "assistant_speech")]
    checks["negatives"] = all(isinstance(r, dict) for r in negatives) and sum(
        r.get("non_command_with_proposal", 0) for r in negatives if isinstance(r, dict)
    ) <= protocol["thresholds"]["max_negative_proposals"]
    checks["physical"] = (physical.get("human_witnessed") is True
        and physical.get("runtime_sha256") == runtime_identity()
        and physical.get("runtime_end_sha256") == runtime_identity()
        and all(physical.get("checks", {}).get(key) is True for key in PHYSICAL_CHECKS))
    report = {"schema_version": 1, "runtime_sha256": runtime_identity(),
              "protocol_sha256": protocol_hash, "references_sha256": references,
              "checks": checks, "missing": missing,
              "qualified": not missing and all(checks.values()),
              "operator_pairing_and_witness_limitations": True,
              "recognition_and_corrected_actions_are_separate": True}
    _write(Path(output), report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "evaluate"])
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--thresholds", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        if args.thresholds is None:
            parser.error("prepare requires predeclared --thresholds")
        print(prepare(args.source, args.thresholds, args.output))
    else:
        report = evaluate(args.source, args.output)
        raise SystemExit(0 if report["qualified"] else 2)


if __name__ == "__main__":
    main()
