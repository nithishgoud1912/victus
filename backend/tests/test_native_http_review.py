"""Real queue/worker/HTTP review with explicitly simulated UIA; never native proof."""

import time
from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient

from victus.adapters.uia.applications import ApplicationProfile, ControlSelector, UIAWorker
from victus.api.app import create_app
from victus.settings import Settings
from victus.tools.registry import RetryClass, RiskLevel, ToolSpec
from victus.workflows.contracts import NOTEPAD_CHECKLIST_TOOL, NotepadChecklistSubmission
from victus.workflows.native_review import (
    reject_unowned,
    reviewed_checklist,
    verify_native_checklist,
)

TOKEN = "native-http-test-" + "x" * 40
HEADERS = {"Authorization": "Bearer " + TOKEN}


@dataclass(frozen=True)
class ReviewedFixture:
    ttl: float = 15

    async def __call__(self, root, args, cancelled, authority):
        from test_notepad_workflow import FakeBackend

        executable = root.parent / "fixture.exe"
        controls = {
            key: ControlSelector(kind, automation_id=key, root_window=window)
            for key, kind, window in (
                ("editor", "Edit", "main"),
                ("file_menu", "MenuItem", "main"),
                ("save_as", "MenuItem", "main"),
                ("filename", "Edit", "save_dialog"),
                ("save", "Button", "save_dialog"),
            )
        }
        profile = ApplicationProfile(
            args.profile,
            executable,
            ControlSelector("Window", automation_id="main"),
            controls,
            windows={"save_dialog": ControlSelector("Window", automation_id="save_dialog")},
        )
        backend = FakeBackend(executable)
        original_windows = backend.windows

        def windows():
            if (root.parent / "change-target").exists():
                backend.editor.element_info.runtime_id = (999, "changed")
            if (root.parent / "change-text").exists():
                backend.editor.value = "changed content"
            return original_windows()

        backend.windows = windows
        set_value = backend.set_value

        def set_filename(control, text):
            result = set_value(control, text)
            if control is backend.filename and (root.parent / "expire-at-filename").exists():
                time.sleep(self.ttl + 0.1)
            return result

        backend.set_value = set_filename
        invoke = backend.invoke

        def checked(control):
            if control is backend.save_button:
                with (root.parent / "save-count").open("a") as stream:
                    stream.write("Save\n")
            return invoke(control)

        backend.invoke = checked
        with UIAWorker((profile,), _backend=backend) as worker:
            return await reviewed_checklist(root, args, cancelled, authority, worker, ttl=self.ttl)


def enable(client, *, ttl=15):
    tasks = client.app.state.services.tasks
    (tasks.workspace.parent / "fixture.exe").write_bytes(b"FAKE ONLY")
    tasks.registry.register(
        ToolSpec(
            name=NOTEPAD_CHECKLIST_TOOL,
            version="test-review",
            description="Simulated reviewed UIA",
            argument_model=NotepadChecklistSubmission,
            risk_floor=RiskLevel.LOW,
            required_scope="fs:write",
            timeout_seconds=40,
            resource_name="workflow_owner",
            retry_class=RetryClass.NONE,
            execute=reject_unowned,
            execute_owned=ReviewedFixture(ttl),
            verify=verify_native_checklist,
        )
    )
    tasks.qualified_notepad_profiles = frozenset({"simulated"})
    tasks.reviewed_notepad_profiles = frozenset({"simulated"})
    return tasks


@pytest.fixture
def client(tmp_path):
    with TestClient(
        create_app(Settings(data_dir=tmp_path / "runtime", api_token=TOKEN)),
        base_url="http://127.0.0.1",
    ) as client:
        yield client


def body(filename="review.txt"):
    return {"profile": "simulated", "filename": filename, "items": ["Inspect <literal>", "Save"]}


def submit(client):
    response = client.post(
        "/api/workflows/notepad-checklist",
        headers={**HEADERS, "X-Client-Request-ID": "stable-request"},
        json=body(),
    )
    assert response.status_code == 202
    return response.json()["task_id"]


def wait(client, task_id, *, review=False):
    end = time.monotonic() + 25
    while time.monotonic() < end:
        result = client.get(f"/api/tasks/{task_id}", headers=HEADERS).json()
        if (
            result["status"] == "waiting_for_review"
            if review
            else result["status"] not in {"queued", "prepared", "running", "waiting_for_review"}
        ):
            return result
        time.sleep(0.03)
    raise AssertionError("Review fixture did not reach expected state")


def resolve(client, approval_id, decision="approved"):
    return client.post(
        f"/api/approvals/{approval_id}/resolve",
        headers=HEADERS,
        json={"decision": decision, "confirmation": "explicit_user_review"},
    )


def test_approve_once_exact_preview_artifact_snapshot_and_duplicate(client):
    tasks = enable(client)
    task_id = submit(client)
    waiting = wait(client, task_id, review=True)
    assert tasks.queue.active_task_id == task_id and tasks.mutation_lock.locked()
    approval = waiting["approval_id"]
    preview = client.get(f"/api/approvals/{approval}/preview", headers=HEADERS).json()
    assert preview["text"] == "Checklist\r\n[ ] Inspect <literal>\r\n[ ] Save\r\n"
    assert preview["destination"].endswith("review.txt")
    # A dropped/renewed HTTP client does not resubmit or approve the task.
    assert client.get(f"/api/tasks/{task_id}", headers=HEADERS).json() == waiting
    assert not (tasks.workspace / "review.txt").exists()
    assert resolve(client, approval).status_code == 200
    assert resolve(client, approval).status_code == 409
    result = wait(client, task_id)
    assert result["status"] == "succeeded" and result["verified"]
    assert (tasks.workspace / "review.txt").read_bytes() == preview["text"].encode()
    assert (tasks.workspace.parent / "save-count").read_text().splitlines() == ["Save"]
    assert submit(client) == task_id
    tasks.reviewed_notepad_profiles = frozenset()
    assert submit(client) == task_id  # Admission becoming unavailable cannot replace an old effect.
    assert client.get(f"/api/approvals/{approval}", headers=HEADERS).json()["state"] == "consumed"


@pytest.mark.parametrize("case", ["deny", "expire", "target", "text", "path", "stop"])
def test_review_failures_prevent_save_and_do_not_replay(client, case):
    tasks = enable(client, ttl=1 if case == "expire" else 15)
    task_id = submit(client)
    waiting = wait(client, task_id, review=True)
    approval = waiting["approval_id"]
    if case == "deny":
        assert resolve(client, approval, "denied").status_code == 200
    elif case == "expire":
        time.sleep(1.1)
    elif case == "stop":
        assert client.post("/api/stop", headers=HEADERS).status_code == 200
    else:
        if case == "path":
            (tasks.workspace / "review.txt").write_bytes(b"preserve existing")
        else:
            (
                tasks.workspace.parent / ("change-target" if case == "target" else "change-text")
            ).touch()
        assert resolve(client, approval).status_code == 200
    result = wait(client, task_id)
    assert not result["verified"] and result["status"] != "succeeded"
    assert not (tasks.workspace.parent / "save-count").exists()
    if case == "path":
        assert (tasks.workspace / "review.txt").read_bytes() == b"preserve existing"
    else:
        assert not (tasks.workspace / "review.txt").exists()
    assert resolve(client, approval).status_code == 409


def test_capabilities_are_read_only_and_both_gates_are_required(client):
    tasks = enable(client)
    before = tasks.database.list_tasks()
    assert client.get("/api/workflows/capabilities").status_code == 401
    assert client.get("/api/workflows/capabilities", headers=HEADERS).json()["notepad_checklist"][
        "enabled"
    ]
    tasks.reviewed_notepad_profiles = frozenset()
    capability = client.get("/api/workflows/capabilities", headers=HEADERS).json()[
        "notepad_checklist"
    ]
    assert not capability["enabled"] and capability["reason"] and not capability["profiles"]
    assert (
        client.post(
            "/api/tasks",
            headers=HEADERS,
            json={"tool": NOTEPAD_CHECKLIST_TOOL, "arguments": body()},
        ).status_code
        == 422
    )
    assert tasks.database.list_tasks() == before


def test_restart_invalidates_waiting_review_without_replaying_save(tmp_path):
    settings = Settings(data_dir=tmp_path / "runtime", api_token=TOKEN)
    with TestClient(create_app(settings), base_url="http://127.0.0.1") as first:
        enable(first)
        task_id = submit(first)
        approval = wait(first, task_id, review=True)["approval_id"]
        assert not (settings.data_dir / "save-count").exists()
    with TestClient(create_app(settings), base_url="http://127.0.0.1") as restarted:
        enable(restarted)
        result = restarted.get(f"/api/tasks/{task_id}", headers=HEADERS).json()
        assert result["status"] == "unknown" and not result["verified"]
        assert resolve(restarted, approval).status_code == 409
        assert submit(restarted) == task_id
        assert not (settings.data_dir / "save-count").exists()
        assert not (settings.workspace / "review.txt").exists()


def test_second_mutation_stays_queued_while_review_owns_worker(client):
    tasks = enable(client)
    task_id = submit(client)
    approval = wait(client, task_id, review=True)["approval_id"]
    second = client.post(
        "/api/tasks",
        headers=HEADERS,
        json={"tool": "fs.create_note", "arguments": {"filename": "second.txt", "text": "later"}},
    )
    assert second.status_code == 202
    assert tasks.database.get(second.json()["task_id"]).status == "queued"
    assert not (tasks.workspace / "second.txt").exists()
    assert resolve(client, approval).status_code == 200
    assert wait(client, task_id)["verified"]
    assert wait(client, second.json()["task_id"])["verified"]


def test_expiry_during_filename_preparation_blocks_native_invoke(client):
    tasks = enable(client, ttl=1)
    (tasks.workspace.parent / "expire-at-filename").touch()
    task_id = submit(client)
    approval = wait(client, task_id, review=True)["approval_id"]
    assert resolve(client, approval).status_code == 200
    assert not wait(client, task_id)["verified"]
    assert not (tasks.workspace.parent / "save-count").exists()
    assert not (tasks.workspace / "review.txt").exists()


def test_capability_keeps_qualification_separate_from_pressure(client, isolated_resources):
    enable(client)
    with isolated_resources._lock:
        isolated_resources._sample["available_bytes"] = 1
    value = client.get("/api/workflows/capabilities", headers=HEADERS).json()
    assert value["resource_blocked"] and value["notepad_checklist"]["enabled"]


def test_startup_recovers_persisted_waiting_state_and_retires_authority(tmp_path):
    from victus.safety.approvals import ApprovalBinding, argument_hash
    from victus.tools.contracts import TaskResult

    settings = Settings(data_dir=tmp_path / "runtime", api_token=TOKEN)
    with TestClient(create_app(settings), base_url="http://127.0.0.1") as first:
        services = first.app.state.services
        action = services.ledger.prepare_action("uia.save_checklist", "0.1.0", {},
                                                expected_effect_ref="task:interrupted-review")
        record = services.approvals.request(ApprovalBinding(
            task_id="interrupted-review", action_id=action, tool_name="uia.save_checklist",
            tool_version="0.1.0", canonical_args_hash=argument_hash({}), policy_version="native-save-v1",
            target_identity="fixture-native", observation_identity="fixture-observation"), {})
        services.tasks.database.save(TaskResult(task_id="interrupted-review",
            tool=NOTEPAD_CHECKLIST_TOOL, status="waiting_for_review", approval_id=record.approval_id))
    with TestClient(create_app(settings), base_url="http://127.0.0.1") as restarted:
        services = restarted.app.state.services
        assert services.tasks.database.get("interrupted-review").status == "unknown"
        assert services.approvals.get(record.approval_id).state == "invalidated"
        assert services.ledger.get(action).status == "cancelled"
        assert not list(settings.workspace.iterdir())


@pytest.mark.parametrize("native,review", [(False, False), (True, False), (False, True)])
def test_native_registration_refuses_either_missing_gate(tmp_path, native, review):
    from victus.workflows.native_review import native_checklist_spec

    with pytest.raises(PermissionError):
        native_checklist_spec(
            tmp_path / "not-read.json",
            {"candidate"},
            native_qualified=native,
            review_qualified=review,
        )
