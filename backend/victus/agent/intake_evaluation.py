"""Read-only supported-phrase diagnostics, separate from the frozen model benchmark."""

import argparse
import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from victus.agent.commands import CommandFields, CommandSubmission, interpret
from victus.models._json import strict_json
from victus.workflows.qualification_records import file_hash, runtime_identity


class Expected(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    rejected: bool = False
    fields: CommandFields = Field(default_factory=CommandFields)
    missing: list[str] = Field(default_factory=list, max_length=6)


class Case(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")
    submission: dict
    expected: Expected


class Suite(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    version: str = Field(min_length=1, max_length=80)
    frozen_before_evaluation: bool
    scope: str = Field(max_length=200)
    cases: list[Case] = Field(min_length=1, max_length=1000)


def evaluate(source, output):
    source, output = Path(source), Path(output)
    if source.stat().st_size > 128000:
        raise ValueError("Bounded intake suite required")
    digest = file_hash(source)
    suite = Suite.model_validate(strict_json(source.read_text()))
    if not suite.frozen_before_evaluation or len({case.id for case in suite.cases}) != len(
        suite.cases
    ):
        raise ValueError("Frozen suite with distinct case IDs required")
    runtime = runtime_identity()
    rows = []
    for case in suite.cases:
        try:
            fields, missing = interpret(CommandSubmission.model_validate(case.submission))
            passed = (
                not case.expected.rejected
                and fields == case.expected.fields
                and missing == case.expected.missing
            )
            actual = {"fields": fields.model_dump(), "missing": missing}
        except (ValueError, TypeError):
            passed = case.expected.rejected
            actual = {"rejected": True}
        rows.append(
            {
                "id": case.id,
                "passed": bool(passed),
                "actual_sha256": hashlib.sha256(
                    json.dumps(actual, sort_keys=True).encode()
                ).hexdigest(),
            }
        )
    if file_hash(source) != digest or runtime_identity() != runtime:
        raise ValueError("Evaluation inputs changed")
    report = {
        "kind": "command_intake_contract",
        "suite_sha256": digest,
        "runtime_sha256": runtime,
        "runtime_end_sha256": runtime_identity(),
        "total": len(rows),
        "passed": sum(row["passed"] for row in rows),
        "cases": rows,
        "model_inference": False,
        "tool_execution": False,
        "model_qualified": False,
        "original_30_goal_gate_replaced": False,
        "status": "passed" if all(row["passed"] for row in rows) else "failed",
    }
    with output.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(report, indent=2) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(0 if evaluate(args.suite, args.output)["status"] == "passed" else 2)


if __name__ == "__main__":
    main()
