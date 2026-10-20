"""Qualification predicates use synthetic reports, never simulated wall time proof."""

import pytest

from victus.runtime.soak_results import finalize


def passing():
    return {
        "elapsed_seconds": 7200,
        "tasks_admitted": 100,
        "tasks_verified": 100,
        "backup_restores": 2,
        "rss_growth_from_warmed_baseline": 0.2,
        "health_p95_seconds": 0.499,
        "failures": [],
        "server_shutdown_complete": True,
        "work_shutdown_complete": True,
        "remaining_multiprocessing_children": 0,
        "implementation_start_sha256": "b" * 64,
        "implementation_end_sha256": "b" * 64,
        "source_start_sha256": "a" * 64,
        "source_end_sha256": "a" * 64,
    }


def test_original_thresholds_after_cleanup():
    report = finalize(passing())
    assert report["qualified"] and not report["smoke_passed"]


@pytest.mark.parametrize(
    "key,value",
    [
        ("elapsed_seconds", 7199),
        ("tasks_verified", 99),
        ("backup_restores", 1),
        ("rss_growth_from_warmed_baseline", 0.201),
        ("health_p95_seconds", 0.5),
        ("health_p95_seconds", float("nan")),
        ("rss_growth_from_warmed_baseline", True),
        ("tasks_verified", 100.0),
        ("tasks_admitted", 101),
        ("failures", ["FAILED"]),
        ("server_shutdown_complete", False),
        ("work_shutdown_complete", False),
        ("remaining_multiprocessing_children", 1),
        ("source_end_sha256", "c" * 64),
        ("implementation_end_sha256", "c" * 64),
    ],
)
def test_no_relaxation_for_missing_threshold_or_cleanup(key, value):
    report = passing()
    report[key] = value
    assert not finalize(report)["qualified"]


def test_short_smoke_success_and_failure_are_distinct():
    report = passing()
    report.update(elapsed_seconds=30, tasks_admitted=4, tasks_verified=4, backup_restores=1)
    assert finalize(report)["smoke_passed"] and not report["qualified"]
    report["failures"].append("FAILED")
    assert not finalize(report)["smoke_passed"]


def test_pressure_abort_is_neither_smoke_nor_qualification():
    report = passing()
    report.update(elapsed_seconds=30, abort_reason="PERSISTENT_RESOURCE_PRESSURE")
    assert not finalize(report)["smoke_passed"] and not report["qualified"]


def test_missing_python_inventory_cannot_qualify():
    report = passing()
    report.pop("implementation_start_sha256")
    report.pop("implementation_end_sha256")
    assert not finalize(report)["qualified"]
