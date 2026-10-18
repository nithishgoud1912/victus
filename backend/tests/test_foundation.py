import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict

from victus.api.app import create_app
from victus.bootstrap import build_services
from victus.settings import Settings
from victus.tools.contracts import ActionRequest, TaskResult
from victus.tools.registry import ToolRegistry, ToolSpec


class TagArguments(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    label: str


def tag_policy(root, args):
    if (root / "typed-tool.txt").exists():
        raise FileExistsError()


def create_tag(root, args):
    target = root / "typed-tool.txt"
    with target.open("xb") as stream:
        stream.write(args.label.encode())
    return target


def verify_tag(target, args):
    return target.read_bytes() == args.label.encode()


TOKEN = "test-only-" + "x" * 40
HEADERS = {"Authorization": f"Bearer {TOKEN}"}


def reject_verification(*_):
    return False


@pytest.fixture
def settings(tmp_path):
    return Settings(data_dir=tmp_path / "runtime", api_token=TOKEN)


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings), base_url="http://127.0.0.1") as test_client:
        yield test_client


def request_body(filename="hello.txt", text="Hello VICTUS"):
    return {"tool": "fs.create_note", "arguments": {"filename": filename, "text": text}}


def test_auth_is_required(client):
    assert client.get("/api/health").status_code == 401


def test_host_and_origin_are_restricted(client):
    assert client.get("/api/health", headers={**HEADERS, "Host": "evil.test"}).status_code == 400
    assert (
        client.get("/api/health", headers={**HEADERS, "Origin": "https://evil.test"}).status_code
        == 403
    )


def wait_for_task(client, task_id: str, timeout: float = 8.0) -> dict:
    start = time.time()
    while time.time() - start < timeout:
        res = client.get(f"/api/tasks/{task_id}", headers=HEADERS).json()
        if res["status"] in {"succeeded", "failed", "cancelled", "unknown"}:
            return res
        time.sleep(0.02)
    raise TimeoutError(f"Task {task_id} did not complete within {timeout}s")


def test_create_and_read_verified_result(client, settings):
    response = client.post("/api/tasks", headers=HEADERS, json=request_body())
    assert response.status_code == 202
    queued = response.json()
    assert queued["status"] == "queued"
    result = wait_for_task(client, queued["task_id"])
    assert result["status"] == "succeeded" and result["verified"]
    assert (settings.workspace / "hello.txt").read_text() == "Hello VICTUS"
    saved = client.get(f"/api/tasks/{result['task_id']}", headers=HEADERS).json()
    assert saved == result


def test_existing_file_is_not_overwritten(client, settings):
    target = settings.workspace / "hello.txt"
    target.write_text("keep me")
    response = client.post("/api/tasks", headers=HEADERS, json=request_body())
    assert response.status_code == 202
    result = wait_for_task(client, response.json()["task_id"])
    assert result["error_code"] == "TARGET_EXISTS"
    assert target.read_text() == "keep me"


@pytest.mark.parametrize("filename", ["../escape.txt", "C:\\escape.txt", "a/b.txt", "a.txt:stream"])
def test_paths_rejected(client, filename):
    assert (
        client.post("/api/tasks", headers=HEADERS, json=request_body(filename)).status_code == 422
    )


def test_reserved_name_denied(client, settings):
    response = client.post("/api/tasks", headers=HEADERS, json=request_body("CON.txt"))
    assert response.status_code == 202
    result = wait_for_task(client, response.json()["task_id"])
    assert result["error_code"] == "POLICY_DENIED"
    assert not (settings.workspace / "CON.txt").exists()


def test_unknown_tool_and_extra_fields_rejected(client):
    body = request_body()
    body["tool"] = "shell.execute"
    assert client.post("/api/tasks", headers=HEADERS, json=body).status_code == 422
    body = request_body()
    body["approved"] = True
    assert client.post("/api/tasks", headers=HEADERS, json=body).status_code == 422


def test_stop_prevents_later_dispatch(client, settings):
    assert client.post("/api/stop", headers=HEADERS).status_code == 200
    result = client.post("/api/tasks", headers=HEADERS, json=request_body()).json()
    assert result["status"] == "cancelled"
    assert not (settings.workspace / "hello.txt").exists()


def test_parallel_duplicate_filename_has_one_winner(client, settings):
    def submit(_):
        res = client.post("/api/tasks", headers=HEADERS, json=request_body())
        assert res.status_code == 202
        return wait_for_task(client, res.json()["task_id"])["status"]

    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(submit, range(2)))
    assert sorted(statuses) == ["failed", "succeeded"]
    assert (settings.workspace / "hello.txt").read_text() == "Hello VICTUS"


def test_restart_preserves_results_and_marks_interrupted_unknown(settings):
    services = build_services(settings)
    result = services.tasks.run(ActionRequest.model_validate(request_body()))
    services.tasks.database.save(
        TaskResult(task_id="interrupted", tool="fs.create_note", status="running")
    )
    services.close()
    resumed = build_services(settings)
    try:
        assert resumed.tasks.database.get(result.task_id).verified
        assert resumed.tasks.database.get("interrupted").status == "unknown"
        assert not (settings.workspace / "interrupted.txt").exists()
    finally:
        resumed.close()


def test_instance_lock_prevents_second_owner(settings):
    first = build_services(settings)
    try:
        with pytest.raises(RuntimeError):
            build_services(settings)
    finally:
        first.close()


def test_failed_verification_is_not_success(settings):
    services = build_services(settings)
    original = services.tasks.registry.get("fs.create_note")
    replacement = ToolRegistry()
    replacement.register(
        ToolSpec(
            name=original.name,
            version=original.version,
            description=original.description,
            argument_model=original.argument_model,
            risk_floor=original.risk_floor,
            required_scope=original.required_scope,
            timeout_seconds=original.timeout_seconds,
            resource_name=original.resource_name,
            retry_class=original.retry_class,
            execute=original.execute,
            verify=reject_verification,
        )
    )
    services.tasks.registry = replacement
    services.tasks.dispatcher.registry = replacement
    try:
        result = services.tasks.run(ActionRequest.model_validate(request_body()))
        assert result.status == "unknown" and not result.verified
        assert result.error_code == "POSTCONDITION_FAILED"
        assert (settings.workspace / "hello.txt").exists()
    finally:
        services.close()


def test_registered_tool_uses_its_own_schema_through_the_task_api(client, settings):
    from dataclasses import replace

    services = client.app.state.services
    services.tasks.registry.register(
        replace(
            services.tasks.registry.get("fs.create_note"),
            name="fixture.write_tag",
            argument_model=TagArguments,
            execute=create_tag,
            verify=verify_tag,
            policy=tag_policy,
        )
    )
    response = client.post(
        "/api/tasks",
        headers=HEADERS,
        json={
            "tool": "fixture.write_tag",
            "arguments": {"label": "tool-specific schema"},
        },
    )
    assert response.status_code == 202
    task = wait_for_task(client, response.json()["task_id"])
    assert task["status"] == "succeeded" and task["verified"]
    assert (settings.workspace / "typed-tool.txt").read_text() == "tool-specific schema"
    record = services.ledger.get(task["action_id"])
    assert record.tool_name == "fixture.write_tag" and record.status == "verified"
    assert record.expected_effect_ref == "task:" + task["task_id"]


@pytest.mark.parametrize(
    "field", ["task_id", "action_id", "approved", "verifier", "scopes", "permit_token"]
)
def test_task_transport_rejects_caller_authority_before_admission(client, settings, field):
    request = request_body()
    request[field] = "forged"
    assert client.post("/api/tasks", headers=HEADERS, json=request).status_code == 422
    with client.app.state.services.tasks.database.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM action_attempts").fetchone()[0] == 0
    assert not (settings.workspace / "hello.txt").exists()


def test_python_submission_is_validated_and_queued_arguments_are_snapshotted(settings):
    services = build_services(settings)
    tasks = services.tasks
    tasks.mutation_lock.acquire()
    try:
        invalid = ActionRequest.model_construct(
            tool="fs.create_note", arguments={"filename": "safe.txt", "text": 7}
        )
        with pytest.raises(ValueError):
            tasks.enqueue(invalid)
        request = ActionRequest.model_validate(request_body())
        task_id, _ = tasks.enqueue(request)
        request.arguments.text = "caller changed this after admission"
    finally:
        tasks.mutation_lock.release()
    try:
        end = time.monotonic() + 8
        while time.monotonic() < end:
            result = tasks.database.get(task_id)
            if result.status not in {"queued", "prepared", "running"}:
                break
            time.sleep(0.02)
        assert result.verified
        assert (settings.workspace / "hello.txt").read_text() == "Hello VICTUS"
    finally:
        services.close()


def test_default_registry_contains_only_qualified_core_tools(client):
    assert client.get("/api/health", headers=HEADERS).json()["tools"] == ["fs.create_note"]
