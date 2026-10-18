"""Read-only evidence for operator-paired English note voice cases, separate from WER."""

import argparse
import hashlib
import json
import re
import sqlite3
from collections import Counter
from contextlib import closing
from pathlib import Path

from victus.storage.action_ledger import _canonical_hash
from victus.voice.transcript_review import review_transcript


def verify_case(root, command_id, reference):
    expected = review_transcript(reference).action
    if expected is None or not re.fullmatch(r"[a-f0-9]{32}", command_id):
        return False
    with closing(
        sqlite3.connect((root / "victus.sqlite3").resolve().as_uri() + "?mode=ro", uri=True)
    ) as db:
        row = db.execute(
            "SELECT request_id,task_id FROM command_intakes WHERE command_id=?", (command_id,)
        ).fetchone()
        if not row or not row[0].startswith("voice-") or not row[1]:
            return False
        task = db.execute("SELECT result_json FROM tasks WHERE task_id=?", (row[1],)).fetchone()
        if task is None:
            return False
        result = json.loads(task[0])
        if result["status"] != "succeeded" or result["verified"] is not True:
            return False
        path = root / "workspace" / expected.arguments.filename
        data = expected.arguments.text.encode("utf-8")
        digest = hashlib.sha256(data).hexdigest()
        if (
            path.is_symlink()
            or not path.is_file()
            or path.read_bytes() != data
            or result["sha256"] != digest
        ):
            return False
        receipt = db.execute(
            "SELECT 1 FROM action_attempts WHERE expected_effect_ref=? AND tool_name=? AND canonical_args_hash=? AND status='verified' AND sha256=?",
            (
                "task:" + row[1],
                expected.tool,
                _canonical_hash(expected.arguments.model_dump()),
                digest,
            ),
        ).fetchone()
        return receipt is not None


def evaluate(manifest, bindings, root):
    labels = json.loads(manifest.read_text())
    pairs = json.loads(bindings.read_text())
    if not isinstance(labels, list) or len(labels) > 1000 or not isinstance(pairs, dict):
        raise ValueError("Bounded label array and ID-to-command-ID bindings required")
    commands = [row for row in labels if row["condition"] in {"quiet", "noisy"}]
    if Counter(row["condition"] for row in commands) != {"quiet": 50, "noisy": 50}:
        raise ValueError("Exactly 50 quiet and 50 noisy command labels required")
    if any(row.get("language") != "en" for row in labels):
        raise ValueError("English labels only")
    if len({row["id"] for row in labels}) != len(labels) or len(set(pairs.values())) != len(pairs):
        raise ValueError("Each case and bound voice command must be distinct")
    rows = []
    for row in commands:
        bound = pairs.get(row["id"])
        rows.append(
            {
                "id": row["id"],
                "condition": row["condition"],
                "measured": bound is not None,
                "verified_correct_action": verify_case(root, bound, row["reference"])
                if bound is not None
                else None,
            }
        )
    groups = {}
    for condition in ["quiet", "noisy"]:
        subset = [row for row in rows if row["condition"] == condition]
        measured = sum(row["measured"] for row in subset)
        correct = sum(row["verified_correct_action"] is True for row in subset)
        groups[condition] = {
            "required": 50,
            "measured": measured,
            "verified_correct_actions": correct,
            "accuracy": correct / measured if measured else None,
            "unmeasured": 50 - measured,
        }
    return {
        "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
        "language": "en",
        "operator_pairs_recording_to_reviewed_session": True,
        "independent_artifact_and_ledger_verification": True,
        "recognition_metrics": "separate audio evaluation required",
        "groups": groups,
        "samples": rows,
        "complete": all(row["measured"] for row in rows),
        "physical_device_qualification": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--bindings", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = evaluate(args.manifest, args.bindings, args.data_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as file:
        file.write(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
