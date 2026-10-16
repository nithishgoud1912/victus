"""Real loopback submissions: approval bindings and lost-response recovery."""

import asyncio
import json

import pytest
from fastapi.testclient import TestClient
from submission_support import SubmissionFixture, submission_server

from victus.agent.graph import agent
from victus.api.app import create_app
from victus.recovery.resume import ResumeManager
from victus.recovery.retry import RetryManager
from victus.safety.permits import PermitStore
from victus.settings import Settings

TOKEN = "m4-fixture-" + "x" * 40
HEADERS = {"Authorization": "Bearer " + TOKEN}


@pytest.mark.parametrize("case", ["deny", "expiry", "reuse", "recipient", "content", "stop"])
def test_submission_approval_boundaries(tmp_path, case):
    with (
        submission_server(tmp_path) as server,
        TestClient(create_app(Settings(tmp_path, TOKEN)), base_url="http://127.0.0.1") as client,
    ):
        fixture = SubmissionFixture(tmp_path, server)
        contexts = []
        execution = fixture.services.execution

        async def capture(state):
            action, context = await execution(state)
            contexts.append(context)
            return action, context

        fixture.services.execution = capture

        async def run():
            async with agent(fixture.services) as runner:
                state = await runner.start(fixture.task, fixture.goal())
                assert state["status"] == "awaiting_approval" and fixture.counts() == (0, 0)
                store = fixture.services.approvals(state)
                record = store.get(state["approval_ref"])
                url = f"/api/approvals/{record.approval_id}/resolve"
                if case == "expiry":
                    with store.connect() as db:
                        db.execute("UPDATE approvals SET expires_at=0")
                if case == "stop":
                    # Stop while the record is still pending, before any confirmation.
                    fixture.services.cancelled = client.app.state.services.tasks.stopped
                    assert client.post("/api/stop", headers=HEADERS).status_code == 200
                response = client.post(
                    url,
                    headers=HEADERS,
                    json={
                        "decision": "denied" if case == "deny" else "approved",
                        "confirmation": "explicit_user_review",
                    },
                )
                assert response.status_code == (409 if case in {"expiry", "stop"} else 200)
                if case == "recipient":
                    fixture.recipient = "changed@fixture.invalid"
                if case == "content":
                    ref = state["current_proposal"]["payload_ref"]
                    proposal = fixture.store.payload(fixture.task, "proposal", ref)
                    proposal["action"]["arguments"]["content"] = "Different content"
                    with fixture.store.connect() as db:
                        db.execute(
                            "UPDATE agent_payloads SET data_json=? WHERE ref=?",
                            (json.dumps(proposal), ref),
                        )
                result = await runner.resume(fixture.task)
                if case == "reuse":
                    assert result["status"] == "succeeded" and fixture.counts() == (1, 1)
                    context = contexts[0]
                    with pytest.raises(PermissionError):
                        PermitStore(store).consume_permit(
                            context.permit_token, context.approval_binding, cancelled=lambda: False
                        )
                    await runner.resume(fixture.task)
                    assert fixture.counts() == (1, 1)
                else:
                    assert result["status"] != "succeeded" and fixture.counts() == (0, 0)

        asyncio.run(run())


def test_timeout_after_committed_receipt_inspects_effect_without_second_post(tmp_path):
    with (
        submission_server(tmp_path, delay=2) as server,
        TestClient(create_app(Settings(tmp_path, TOKEN)), base_url="http://127.0.0.1") as client,
    ):
        fixture = SubmissionFixture(tmp_path, server)

        async def run():
            async with agent(fixture.services) as runner:
                state = await runner.start(fixture.task, fixture.goal())
                approval_id = state["approval_ref"]
                response = client.post(
                    f"/api/approvals/{approval_id}/resolve",
                    headers=HEADERS,
                    json={"decision": "approved", "confirmation": "explicit_user_review"},
                )
                assert response.status_code == 200
                result = await runner.resume(fixture.task)
                assert result["status"] == "unknown" and fixture.counts() == (1, 1)
                action_id = result["action_ledger_refs"][0]
                assert fixture.reconciler.ledger.get(action_id).status == "unknown"
                proof = fixture.reconciler.latest(action_id)
                assert proof.verdict == "present"
                evidence = fixture.reconciler.payloads.get(proof.evidence_ref)
                assert json.loads(evidence.data_json)["receipt_id"]
                retry = RetryManager(fixture.reconciler.ledger)
                with pytest.raises(PermissionError):
                    retry.reserve(
                        action_id,
                        fixture.dispatcher.registry.get("fixture.submit"),
                        result["remaining"],
                        cancelled=lambda: False,
                    )
                # Restart recovery runs only receipt lookups and retires old authority.
                resume = ResumeManager(
                    fixture.reconciler.ledger, fixture.services.approvals(result)
                )
                proofs = await resume.resume(
                    fixture.reconciler, quiesced=True, task_id=fixture.task
                )
                assert proofs[0].verdict == "present"
                await runner.resume(fixture.task)
                assert fixture.counts() == (1, 1)
                assert fixture.services.approvals(result).get(approval_id).state == "consumed"

        asyncio.run(run())
