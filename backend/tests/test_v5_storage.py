"""Durable journal invariants and actual spawned-process storage diagnostics."""

import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from victus.runtime.storage_diagnostics import probe
from victus.storage.checkpoints import CheckpointStore


def test_completion_requires_a_claim_and_cannot_replace_a_completed_result(tmp_path):
    store = CheckpointStore(tmp_path)
    with pytest.raises(ValueError, match="claimed"):
        store.complete("task", 0, {"status": "succeeded"})
    assert store.claim("task", 0, "execute") == ("new", None)
    store.complete("task", 0, {"status": "unknown"})
    with pytest.raises(ValueError, match="claimed"):
        store.complete("task", 0, {"status": "succeeded"})
    assert store.claim("task", 0, "execute") == ("complete", {"status": "unknown"})


def test_two_completers_have_one_durable_winner(tmp_path):
    store = CheckpointStore(tmp_path)
    store.claim("task", 0, "execute")

    def complete(value):
        try:
            store.complete("task", 0, {"value": value})
            return value
        except ValueError:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        winners = [x for x in pool.map(complete, [1, 2]) if x is not None]
    assert len(winners) == 1
    assert CheckpointStore(tmp_path).claim("task", 0, "execute") == (
        "complete",
        {"value": winners[0]},
    )


def test_failed_serialization_leaves_claim_incomplete_for_safe_recovery(tmp_path):
    store = CheckpointStore(tmp_path)
    store.claim("task", 0, "execute")
    with pytest.raises((ValueError, TypeError)):
        store.complete("task", 0, {"unsafe": object()})
    assert store.claim("task", 0, "execute") == ("interrupted", None)
    store.complete("task", 0, {"status": "unknown"})
    assert store.claim("task", 0, "execute")[1] == {"status": "unknown"}


def test_spawned_commit_hard_exit_and_reopen_are_measured(tmp_path):
    report = probe(tmp_path / "probe", repetitions=2)
    assert report["status"] == "passed" and report["qualified"] is False
    assert len(report["cases"]) == 2
    assert all(c["exit_code"] == 73 and c["passed"] for c in report["cases"])
    assert report["runtime_sha256"] == report["runtime_end_sha256"]
    assert json.loads((tmp_path / "probe/report.json").read_text()) == report
    assert str(tmp_path) not in json.dumps(report)
    with pytest.raises(FileExistsError):
        probe(tmp_path / "probe", repetitions=1)


@pytest.mark.parametrize("value", [0, 21, True, 1.5])
def test_probe_repetition_limit_has_no_side_effect(tmp_path, value):
    with pytest.raises(ValueError):
        probe(tmp_path / "probe", repetitions=value)
    assert not (tmp_path / "probe").exists()


def test_probe_refuses_linked_parent_without_modifying_target(tmp_path):
    actual = tmp_path / "actual"
    actual.mkdir()
    linked = tmp_path / "linked"
    linked.symlink_to(actual, target_is_directory=True)
    with pytest.raises(ValueError, match="Linked"):
        probe(linked / "probe", repetitions=1)
    assert not list(actual.iterdir())


def test_child_failure_is_retained_and_stops_campaign(tmp_path, monkeypatch):
    class Child:
        pid = None
        exitcode = 1

        def start(self):
            raise OSError("private failure path must not be exported")

        def is_alive(self):
            return False

        def close(self):
            pass

    import victus.runtime.storage_diagnostics as diagnostics

    monkeypatch.setattr(
        diagnostics.multiprocessing,
        "get_context",
        lambda _: type("Context", (), {"Process": lambda self, **kwargs: Child()})(),
    )
    report = probe(tmp_path / "probe", repetitions=3)
    assert report["status"] == "failed"
    assert report["cases"] == [{"sequence": 0, "passed": False, "error_code": "OSError"}]
    assert "private failure" not in json.dumps(report)
    assert json.loads((tmp_path / "probe/report.json").read_text()) == report
