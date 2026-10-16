import asyncio
import json
from collections import Counter
from pathlib import Path

from victus.agent.benchmark import Case
from victus.models.contracts import ModelPin


def test_frozen_suite_has_thirty_unique_balanced_goals():
    path = Path(__file__).parents[2] / "evaluation/m3-30-goals-v1.json"
    suite = json.loads(path.read_text())
    assert suite["frozen_before_live_run"] is True
    assert len({goal["id"] for goal in suite["goals"]}) == 30
    assert Counter(goal["category"] for goal in suite["goals"]) == {
        "browser": 10,
        "desktop": 10,
        "mixed_file": 10,
    }


def test_benchmark_goal_verifier_checks_exact_bytes_and_extra_destinations(tmp_path):
    goal = {
        "id": "F",
        "category": "mixed_file",
        "request": "Create two files",
        "files": {"a.txt": "one", "b.txt": "two"},
    }
    case = Case(
        tmp_path / "case", goal, None, ModelPin(name="fixture:1", digest="sha256:" + "a" * 64)
    )

    async def verify():
        assert not await case.verify_goal(None, [])
        (case.workspace / "a.txt").write_text("one", encoding="utf-8")
        assert not await case.verify_goal(None, ["receipt"])
        (case.workspace / "b.txt").write_text("wrong", encoding="utf-8")
        assert not await case.verify_goal(None, ["receipt"])
        (case.workspace / "b.txt").write_text("two", encoding="utf-8")
        assert await case.verify_goal(None, ["receipt"])
        (case.workspace / "unexpected.txt").write_text("extra", encoding="utf-8")
        assert not await case.verify_goal(None, ["receipt"])
        assert await case.unexpected_targets() == ["unexpected.txt"]

    asyncio.run(verify())


def test_desktop_benchmark_cannot_simulate_native_proof(tmp_path):
    case = Case(
        tmp_path / "desktop",
        {"id": "D", "category": "desktop", "request": "Open Notepad"},
        None,
        ModelPin(name="fixture:1", digest="sha256:" + "a" * 64),
    )
    assert case.registry.tools() == []
    assert asyncio.run(case.verify_goal(None, ["fake receipt"])) is False
