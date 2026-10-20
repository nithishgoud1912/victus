"""Original core-soak thresholds, evaluated only after cleanup completes."""

import math
import re


def _number(value):
    return type(value) in {int, float} and math.isfinite(value)


def finalize(report):
    cleanup = (
        report.get("server_shutdown_complete") is True
        and report.get("work_shutdown_complete") is True
        and type(report.get("remaining_multiprocessing_children")) is int
        and report["remaining_multiprocessing_children"] == 0
    )
    source = report.get("source_start_sha256")
    implementation = report.get("implementation_start_sha256")
    source_unchanged = (
        isinstance(source, str)
        and re.fullmatch(r"[a-f0-9]{64}", source) is not None
        and source == report.get("source_end_sha256")
        and isinstance(implementation, str)
        and re.fullmatch(r"[a-f0-9]{64}", implementation) is not None
        and implementation == report.get("implementation_end_sha256")
    )
    elapsed = report.get("elapsed_seconds")
    full = _number(elapsed) and elapsed >= 7200
    failures = report.get("failures")
    healthy = (
        type(failures) is list
        and not failures
        and not report.get("abort_reason")
        and cleanup
        and source_unchanged
    )
    tasks, backups = report.get("tasks_verified"), report.get("backup_restores")
    counts = (
        type(tasks) is int
        and type(backups) is int
        and type(report.get("tasks_admitted")) is int
        and report["tasks_admitted"] == tasks
    )
    rss, latency = report.get("rss_growth_from_warmed_baseline"), report.get("health_p95_seconds")
    metrics = _number(rss) and 0 <= rss <= 0.20 and _number(latency) and 0 <= latency < 0.5
    report["cleanup_complete"] = cleanup
    report["source_unchanged"] = source_unchanged
    report["full_two_hour_soak"] = bool(full)
    report["qualified"] = bool(
        healthy and full and counts and tasks >= 100 and backups >= 2 and metrics
    )
    report["smoke_passed"] = bool(healthy and not full and counts and tasks > 0 and backups > 0)
    report["status"] = (
        "qualified"
        if report["qualified"]
        else ("smoke_passed" if report["smoke_passed"] else "incomplete_or_failed")
    )
    return report
