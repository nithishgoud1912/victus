"""Prepare and assemble private, operator-supervised native qualification sessions.

Preparing a session performs no desktop effect. Case/DPI observations are explicit
operator evidence, not cryptographic attestations or substitutes for real runs.
"""

import json
from pathlib import Path

from victus.workflows.qualification_records import (
    NATIVE_CHECKS,
    _native_profile,
    _validate_report,
    _validate_runs,
    file_hash,
    promote_native,
    read_record,
    runtime_identity,
)


def _write(path, value):
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2) + "\n")


def prepare_session(output, profile):
    if not profile or Path(profile).name != profile:
        raise ValueError("Installed profile ID required")
    import sys

    from victus.adapters.uia.applications import load_profiles

    root = (
        Path(sys._MEIPASS) if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[3]
    )
    profiles_file = root / "config/applications" / (profile + ".json")
    (selected,) = [item for item in load_profiles(profiles_file) if item.name == profile]
    identity = dict(
        runtime_sha256=runtime_identity(),
        profile=profile,
        profiles_sha256=file_hash(profiles_file),
        executable_sha256=file_hash(selected.executable),
    )
    _native_profile(identity)
    output = Path(output).absolute()
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    (output / "cases").mkdir(mode=0o700)
    (output / "runs").mkdir(mode=0o700)
    for name in sorted(NATIVE_CHECKS):
        _write(
            output / "cases" / (name + ".json"),
            {
                "schema_version": 2,
                **identity,
                "check": name,
                "runtime_end_sha256": None,
                "passed": False,
                "real_windows": False,
                "normal_memory_guards": False,
                "status": "not_performed",
                "evidence": [],
            },
        )
    for index in (1, 2):
        _write(
            output / f"dpi-{index}.json",
            {
                "schema_version": 2,
                **identity,
                "runtime_end_sha256": None,
                "dpi": None,
                "physical_observed": False,
                "real_windows": False,
                "passed": False,
                "status": "not_performed",
            },
        )
    _write(
        output / "session.json",
        {
            "schema_version": 2,
            "kind": "native_session",
            **identity,
            "human_observation_required": True,
            "instructions": "Retain real run reports in runs/<new-root>/notepad-qualification.json. "
            "Complete each case/DPI record only after the observed operation; "
            "bind its retained evidence file/hash. Then assemble-native. "
            "Source or installed profile changes require a new session.",
        },
    )
    return output / "session.json"


def assemble_session(session_file, output):
    session_file = Path(session_file).absolute()
    session, _ = read_record(session_file)
    if (
        session.get("kind") != "native_session"
        or session.get("runtime_sha256") != runtime_identity()
    ):
        raise ValueError("Current prepared native session required")
    _native_profile(session)
    root = session_file.parent
    output = Path(output).absolute()
    if output.parent != root:
        raise ValueError("Assembled report must remain in its session directory")
    runs = []
    checks = {}
    references = {}
    missing = []
    for index, path in enumerate(sorted((root / "runs").glob("*/notepad-qualification.json"))):
        try:
            report, report_hash = read_record(path)
            items = report.get("runs")
            if (
                type(report.get("schema_version")) is not int
                or report["schema_version"] != 2
                or report.get("kind") != "notepad"
                or report.get("status") != "succeeded"
                or report.get("native_windows") is not True
                or report.get("normal_memory_guards") is not True
                or report.get("runtime_sha256") != session["runtime_sha256"]
                or report.get("runtime_end_sha256") != session["runtime_sha256"]
                or any(
                    report.get(key) != session[key]
                    for key in ("profile", "profiles_sha256", "executable_sha256")
                )
                or not isinstance(items, list)
                or not 1 <= len(items) <= 1000
                or any(not isinstance(item, dict) for item in items)
            ):
                raise ValueError("Invalid native run report")
            runs.extend(
                {
                    **item,
                    "run_root": path.parent.relative_to(root).as_posix(),
                    "run_report_sha256": report_hash,
                }
                for item in items
            )
        except (OSError, ValueError, KeyError, TypeError):
            # Keep usable evidence and report a bounded identifier, never exception text.
            missing.append(f"invalid_run_report:{index + 1}")
    for name in sorted(NATIVE_CHECKS):
        path = root / "cases" / (name + ".json")
        valid = False
        try:
            case, digest = read_record(path)
            references[name] = {"file": path.relative_to(root).as_posix(), "sha256": digest}
            evidence = case.get("evidence")
            valid = (
                type(case.get("schema_version")) is int
                and case["schema_version"] == 2
                and case.get("check") == name
                and case.get("passed") is True
                and case.get("real_windows") is True
                and case.get("normal_memory_guards") is True
                and case.get("runtime_sha256") == runtime_identity()
                and case.get("runtime_end_sha256") == runtime_identity()
                and all(
                    case.get(key) == session[key]
                    for key in ("profile", "profiles_sha256", "executable_sha256")
                )
                and isinstance(evidence, list)
                and bool(evidence)
            )
            if valid:
                for reference in evidence:
                    relative = Path(reference["file"])
                    if relative.is_absolute() or relative.drive or ".." in relative.parts:
                        raise ValueError("Case evidence must stay beneath session")
                    if file_hash(root / relative) != reference.get("sha256"):
                        raise ValueError("Case evidence changed")
        except (OSError, ValueError, KeyError, TypeError):
            valid = False
        checks[name] = bool(valid)
        if not valid:
            missing.append(name)
    dpi, dpi_refs = [], []
    for path in (root / "dpi-1.json", root / "dpi-2.json"):
        try:
            observed, digest = read_record(path)
            if not (
                observed.get("physical_observed") is True
                and observed.get("real_windows") is True
                and observed.get("passed") is True
                and type(observed.get("dpi")) is int
                and 72 <= observed["dpi"] <= 768
                and observed.get("runtime_sha256") == runtime_identity()
                and observed.get("runtime_end_sha256") == runtime_identity()
                and all(
                    observed.get(key) == session[key]
                    for key in ("profile", "profiles_sha256", "executable_sha256")
                )
            ):
                raise ValueError("Physical DPI observation unavailable")
            dpi.append(observed["dpi"])
            dpi_refs.append({"file": path.name, "sha256": digest})
        except (OSError, ValueError, KeyError, TypeError):
            missing.append(path.stem)
    report = {
        "schema_version": 2,
        "kind": "native",
        **{
            key: session[key]
            for key in ("runtime_sha256", "profile", "profiles_sha256", "executable_sha256")
        },
        "runtime_end_sha256": runtime_identity(),
        "runs": runs,
        "verified_runs": len(runs),
        "physical_dpi": dpi,
        "dpi_reports": dpi_refs,
        "checks": checks,
        "case_reports": references,
        "normal_memory_guards": True,
        "operator_observed_cases": True,
        "missing": missing,
        "passed": False,
        "qualified": False,
    }
    try:
        _validate_runs(report, output, ".txt")
        if len(set(dpi)) < 2 or missing:
            raise ValueError("Outstanding native observations")
        report.update(passed=True, qualified=True)
        _validate_report(report, "native", NATIVE_CHECKS)
    except (OSError, ValueError, KeyError, TypeError):
        report["missing"].append("complete_matching_runs_and_physical_case_evidence")
        report.update(passed=False, qualified=False)
    _write(output, report)
    return output


__all__ = ["prepare_session", "assemble_session", "promote_native"]
