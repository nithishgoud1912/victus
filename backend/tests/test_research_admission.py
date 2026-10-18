"""Queue/API boundary fixtures. Does not establish a real browser qualification."""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from victus.api.app import create_app
from victus.settings import Settings
from victus.tools.registry import RetryClass, RiskLevel, ToolSpec
from victus.workflows.contracts import BROWSER_RESEARCH_TOOL, BrowserResearchSubmission

TOKEN = "research-test-" + "r" * 40
HEADERS = {"Authorization": "Bearer " + TOKEN, "X-Client-Request-ID": "research-one"}
BODY = {"source_ids": ["source-a", "source-b"], "required_sources": 2, "filename": "sources.json"}


async def execute_fixture(root, args):
    path = root / args.filename
    with path.open("xb") as file:
        file.write(b"fixture report")
    return path


def verify_fixture(path, args):
    return path.read_bytes() == b"fixture report"


@pytest.fixture
def client(tmp_path):
    with TestClient(
        create_app(Settings(data_dir=tmp_path / "runtime", api_token=TOKEN)),
        base_url="http://127.0.0.1",
    ) as client:
        yield client


def enable_fixture(client):
    tasks = client.app.state.services.tasks
    binary = tasks.workspace.parent / "fixture-browser"
    binary.write_bytes(b"not an executable; never launched")
    tasks.research = SimpleNamespace(browser_executable=str(binary))
    tasks.registry.register(
        ToolSpec(
            name=BROWSER_RESEARCH_TOOL,
            version="fixture",
            description="Admission fixture",
            argument_model=BrowserResearchSubmission,
            risk_floor=RiskLevel.LOW,
            required_scope="fs:write",
            timeout_seconds=5,
            resource_name="workflow_owner",
            retry_class=RetryClass.NONE,
            execute=execute_fixture,
            verify=verify_fixture,
        )
    )
    return tasks, binary


def test_absent_prerequisite_and_generic_route_are_gated(client):
    assert (
        client.post("/api/workflows/browser-research", headers=HEADERS, json=BODY).status_code
        == 503
    )
    assert (
        client.post(
            "/api/tasks", headers=HEADERS, json={"tool": BROWSER_RESEARCH_TOOL, "arguments": BODY}
        ).status_code
        == 422
    )
    assert not client.app.state.services.tasks.database.list_tasks()


@pytest.mark.parametrize(
    "change",
    [
        {"source_ids": ["https://example.org"]},
        {"source_ids": ["http://169.254.169.254/"]},
        {"filename": "../bad.json"},
        {"profile": "user-browser"},
        {"approved": True},
        {"required_sources": 0},
        {"source_ids": []},
        {"browser_executable": "C:/evil.exe"},
    ],
)
def test_caller_cannot_expand_scope_or_supply_authority(client, change):
    assert (
        client.post(
            "/api/workflows/browser-research", headers=HEADERS, json={**BODY, **change}
        ).status_code
        == 422
    )
    assert not client.app.state.services.tasks.database.list_tasks()


def test_replay_prerequisite_conflict_stop_and_generic_admission(client):
    from test_command_admission import terminal

    tasks, binary = enable_fixture(client)
    response = client.post("/api/workflows/browser-research", headers=HEADERS, json=BODY)
    assert response.status_code == 202, response.text
    task_id = response.json()["task_id"]
    assert terminal(client, task_id, HEADERS)["verified"]
    binary.unlink()
    unavailable = client.post(
        "/api/commands",
        headers={**HEADERS, "X-Client-Request-ID": "nl-missing"},
        json={"text": "research sources source-a into absent.json"},
    )
    assert unavailable.json()["state"] == "unavailable"
    assert (
        client.post("/api/workflows/browser-research", headers=HEADERS, json=BODY).json()["task_id"]
        == task_id
    )
    assert (
        client.post(
            "/api/workflows/browser-research",
            headers={**HEADERS, "X-Client-Request-ID": "missing"},
            json={**BODY, "filename": "missing.json"},
        ).status_code
        == 503
    )
    binary.write_bytes(b"fixture")
    assert (
        client.post(
            "/api/workflows/browser-research",
            headers={**HEADERS, "X-Client-Request-ID": "conflict"},
            json=BODY,
        ).status_code
        == 422
    )
    response = client.post(
        "/api/tasks",
        headers={**HEADERS, "X-Client-Request-ID": "generic"},
        json={"tool": BROWSER_RESEARCH_TOOL, "arguments": {**BODY, "filename": "generic.json"}},
    )
    assert terminal(client, response.json()["task_id"], HEADERS)["verified"]
    client.post("/api/stop", headers=HEADERS)
    stopped = client.post(
        "/api/workflows/browser-research",
        headers={**HEADERS, "X-Client-Request-ID": "stopped"},
        json={**BODY, "filename": "stopped.json"},
    )
    assert stopped.json()["status"] == "cancelled"
    assert not (tasks.workspace / "stopped.json").exists()
