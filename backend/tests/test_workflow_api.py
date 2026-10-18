"""Narrow HTTP admission contracts; the only enabled adapter here is simulated."""

import time
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from victus.adapters.uia.applications import ApplicationProfile, ControlSelector, UIAWorker
from victus.api.app import create_app
from victus.settings import Settings
from victus.tasks.queue import QueueFullError
from victus.tools.dispatcher import Dispatcher
from victus.tools.registry import RetryClass, RiskLevel, ToolRegistry, ToolSpec
from victus.workflows.common import bytes_match, context_for, new_destination
from victus.workflows.contracts import NOTEPAD_CHECKLIST_TOOL, NotepadChecklistSubmission
from victus.workflows.create_notepad_checklist import (
    ChecklistRequest,
    NotepadTools,
    create_notepad_checklist,
)

TOKEN = "workflow-test-" + "x" * 40
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
ROUTE = "/api/workflows/notepad-checklist"


async def fake_checklist(root, args, cancelled=None):
    from test_notepad_workflow import FakeBackend

    executable = root.parent / "fixture-notepad.exe"
    controls = {
        key: ControlSelector(kind, automation_id=key, root_window=window)
        for key, kind, window in (
            ("editor", "Edit", "main"), ("file_menu", "MenuItem", "main"),
            ("save_as", "MenuItem", "main"), ("filename", "Edit", "save_dialog"),
            ("save", "Button", "save_dialog"),
        )
    }
    profile = ApplicationProfile(
        args.profile, executable, ControlSelector("Window", automation_id="main"), controls,
        windows={"save_dialog": ControlSelector("Window", automation_id="save_dialog")},
    )
    request = ChecklistRequest(**args.model_dump())
    with UIAWorker((profile,), _backend=FakeBackend(executable)) as worker:
        tools = NotepadTools(worker, request, root)
        registry = ToolRegistry()
        tools.register(registry)
        context = context_for(
            root, uuid4().hex, cancelled,
            {"desktop:launch", "desktop:read", "desktop:interact", "filesystem:save", "filesystem:read"},
            tools.authorize, max_unreviewed_risk=RiskLevel.HIGH,
        )
        # This fake-only fixture runs inside the real queue's supervised owner.
        context.resource_owned = True
        result = await create_notepad_checklist(Dispatcher(root, registry), context, request)
        if result.status != "succeeded":
            raise RuntimeError("Simulated checklist was not verified")
    return root / args.filename


def verify_fake_checklist(path, args):
    return bytes_match(path, ChecklistRequest(**args.model_dump()).editor_text().encode())


def fake_policy(root, args):
    if args.profile != "fixture-notepad":
        raise PermissionError("Unsupported fixture")
    new_destination(root, args.filename)


@pytest.fixture
def client(tmp_path):
    settings = Settings(data_dir=tmp_path / "runtime", api_token=TOKEN)
    with TestClient(create_app(settings), base_url="http://127.0.0.1") as client:
        yield client


def enable_fake(client):
    tasks = client.app.state.services.tasks
    executable = tasks.workspace.parent / "fixture-notepad.exe"
    executable.write_bytes(b"SIMULATED ONLY; NEVER LAUNCHED")
    tasks.registry.register(ToolSpec(
        name=NOTEPAD_CHECKLIST_TOOL, version="fixture", description="Simulated UIA fixture only",
        argument_model=NotepadChecklistSubmission, risk_floor=RiskLevel.LOW,
        required_scope="fs:write", timeout_seconds=30, resource_name="workflow_owner",
        retry_class=RetryClass.NONE, execute=fake_checklist, verify=verify_fake_checklist,
        execute_cancellable=fake_checklist, policy=fake_policy,
    ))
    tasks.qualified_notepad_profiles = frozenset({"fixture-notepad"})
    tasks.reviewed_notepad_profiles = frozenset({"fixture-notepad"})
    return tasks


def body(**changes):
    return {"profile": "fixture-notepad", "items": ["Inspect", "Save", "Verify"], "filename": "checklist.txt", **changes}


def count_tasks(client):
    with client.app.state.services.tasks.database.connect() as db:
        return db.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]


def terminal(client, task_id):
    end = time.monotonic() + 20
    while time.monotonic() < end:
        result = client.get(f"/api/tasks/{task_id}", headers=HEADERS).json()
        if result["status"] not in {"queued", "prepared", "running"}:
            return result
        time.sleep(.02)
    raise AssertionError("Fixture task did not finish")


def test_native_is_unavailable_before_admission_and_generic_route_cannot_bypass(client):
    assert client.post(ROUTE, json=body(), headers=HEADERS).status_code == 503
    assert client.post("/api/tasks", headers=HEADERS, json={
        "tool": NOTEPAD_CHECKLIST_TOOL, "arguments": body(),
    }).status_code == 422
    assert count_tasks(client) == 0


def test_registered_tool_cannot_bypass_service_profile_gate_through_generic_route(client):
    tasks = enable_fake(client)
    tasks.qualified_notepad_profiles = frozenset()
    response = client.post("/api/tasks", headers=HEADERS, json={
        "tool": NOTEPAD_CHECKLIST_TOOL, "arguments": body(),
    })
    assert response.status_code == 422 and count_tasks(client) == 0
    tasks.qualified_notepad_profiles = frozenset({"fixture-notepad"})
    response = client.post("/api/tasks", headers=HEADERS, json={
        "tool": NOTEPAD_CHECKLIST_TOOL, "arguments": body(profile="unqualified"),
    })
    assert response.status_code == 422 and count_tasks(client) == 0


def test_workflow_preserves_auth_host_and_origin_restrictions(client):
    assert client.post(ROUTE, json=body()).status_code == 401
    assert client.post(ROUTE, json=body(), headers={**HEADERS, "Host": "evil.test"}).status_code == 400
    assert client.post(ROUTE, json=body(), headers={**HEADERS, "Origin": "https://evil.test"}).status_code == 403
    assert count_tasks(client) == 0


@pytest.mark.parametrize("extra", [
    "approved", "executable", "profiles_file", "root", "selectors", "allow_keyboard",
    "encoding", "task_id", "action_id", "permit_token",
])
def test_authority_and_native_configuration_are_not_workflow_inputs(client, extra):
    assert client.post(ROUTE, json=body(**{extra: True}), headers=HEADERS).status_code == 422
    assert count_tasks(client) == 0


@pytest.mark.parametrize("changes", [
    {"filename": "../outside.txt"}, {"filename": "C:/outside.txt"},
    {"profile": "../profiles.json"}, {"items": []}, {"items": [""]},
    {"items": ["a\nb"]}, {"items": ["x" * 161]}, {"items": [7]},
    {"items": ["x"] * 51}, {"items": ["x" * 160] * 50},
])
def test_invalid_commands_fail_before_queue_admission(client, changes):
    assert client.post(ROUTE, json=body(**changes), headers=HEADERS).status_code == 422
    assert count_tasks(client) == 0


def test_supported_fake_uses_queue_dispatcher_verifiers_and_dedup_after_file_creation(client):
    tasks = enable_fake(client)
    headers = {**HEADERS, "X-Client-Request-ID": "same-checklist-request"}
    queued = client.post(ROUTE, json=body(), headers=headers)
    assert queued.status_code == 202
    task_id = queued.json()["task_id"]
    result = terminal(client, task_id)
    assert result["status"] == "succeeded" and result["verified"]
    expected = ChecklistRequest(**body()).editor_text().encode()
    assert (tasks.workspace / "checklist.txt").read_bytes() == expected
    duplicate = client.post(ROUTE, json=body(items=["Changed request"]), headers=headers)
    assert duplicate.status_code == 202 and duplicate.json()["task_id"] == task_id
    assert count_tasks(client) == 1
    assert (tasks.workspace / "checklist.txt").read_bytes() == expected
    # Reload/snapshot reads do not submit a second action.
    for _ in range(3):
        assert client.get(f"/api/tasks/{task_id}", headers=HEADERS).json() == result
    assert count_tasks(client) == 1
    rows = tasks.events.get_events(task_id=task_id)
    assert [r.event_type for r in rows].count("task.started") == 1
    assert "Changed request" not in repr(rows)


def test_concurrent_workflow_admission_deduplicates_before_destination_check(client):
    tasks = enable_fake(client)
    headers = {**HEADERS, "X-Client-Request-ID": "concurrent-checklist"}
    with ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(pool.map(
            lambda _: client.post(ROUTE, json=body(), headers=headers), range(8)
        ))
    assert all(r.status_code == 202 for r in responses)
    task_ids = {r.json()["task_id"] for r in responses}
    assert len(task_ids) == 1 and count_tasks(client) == 1
    result = terminal(client, task_ids.pop())
    assert result["verified"] and result["status"] == "succeeded"
    assert (tasks.workspace / "checklist.txt").read_bytes() == ChecklistRequest(**body()).editor_text().encode()


@pytest.mark.parametrize("case", ["unsupported", "existing", "reserved"])
def test_invalid_supported_workflow_does_not_admit_or_replace(client, case):
    tasks = enable_fake(client)
    target = tasks.workspace / "checklist.txt"
    changes = {}
    if case == "unsupported":
        changes["profile"] = "unreviewed-profile"
    elif case == "existing":
        target.write_bytes(b"preserve existing bytes")
    else:
        changes["filename"] = "CON.txt"
    assert client.post(ROUTE, json=body(**changes), headers=HEADERS).status_code == 422
    assert count_tasks(client) == 0
    if case == "existing":
        assert target.read_bytes() == b"preserve existing bytes"


def test_stop_uses_same_service_and_never_runs_fake_adapter(client):
    tasks = enable_fake(client)
    assert client.post("/api/stop", headers=HEADERS).status_code == 200
    response = client.post(ROUTE, json=body(), headers=HEADERS)
    assert response.status_code == 202 and response.json()["status"] == "cancelled"
    assert not (tasks.workspace / "checklist.txt").exists()


def test_queue_full_has_existing_backpressure_status(client, monkeypatch):
    tasks = enable_fake(client)

    def full(*args, **kwargs):
        raise QueueFullError()

    monkeypatch.setattr(tasks.queue, "submit", full)
    assert client.post(ROUTE, json=body(), headers=HEADERS).status_code == 429
    assert count_tasks(client) == 0
