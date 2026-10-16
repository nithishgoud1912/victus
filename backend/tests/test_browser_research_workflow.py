"""Source accounting cannot be satisfied by summaries or repeated observations."""

import asyncio
import json
from types import SimpleNamespace

import pytest

from victus.tools.contracts import ActionProposal
from victus.tools.dispatcher import Dispatcher
from victus.tools.registry import ToolRegistry
from victus.workflows.browser_research import BrowserResearchTools, ResearchRequest
from victus.workflows.common import context_for, digest


@pytest.mark.parametrize("required,complete", [(1, True), (2, False)])
def test_only_distinct_verified_sources_count(tmp_path, required, complete):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    session = SimpleNamespace(
        _browser=SimpleNamespace(version="simulation"),
        _device_scale_factor=1,
        _browser_executable=None,
    )
    request = ResearchRequest(
        fixture_origin="http://127.0.0.1:1234",
        source_urls=["http://127.0.0.1:1234/a"],
        required_sources=required,
        filename="research.json",
    )
    tools = BrowserResearchTools(session, request, workspace)
    # Stand in for two independently verified observations of the SAME source URL.
    for ref in ("one", "two"):
        tools.sources[ref] = dict(
            url=request.source_urls[0],
            title="Source",
            text="Observed text",
            observation_id=ref,
            text_sha256=digest(b"Observed text"),
        )
    registry = ToolRegistry()
    tools.register(registry)
    context = context_for(
        workspace, "accounting", None, {"content:generate", "filesystem:save"}, tools.authorize
    )
    dispatcher = Dispatcher(workspace, registry)

    async def run():
        forged = await dispatcher.dispatch_step(
            ActionProposal(tool="research.generate_summary", arguments={"source_refs": ["forged"]}),
            context,
        )
        assert forged.status == "blocked"
        summary = await dispatcher.dispatch_step(
            ActionProposal(
                tool="research.generate_summary", arguments={"source_refs": ["one", "two"]}
            ),
            context,
        )
        assert summary.verified
        output = await dispatcher.dispatch_step(
            ActionProposal(
                tool="research.publish_sources",
                arguments=dict(
                    source_refs=["one", "two"],
                    summary_ref=summary.data["summary_ref"],
                    filename="research.json",
                ),
            ),
            context,
        )
        assert output.verified  # Artifact proof is separate from the task's source promise.
        assert output.data["complete"] is complete

    asyncio.run(run())
    report = json.loads((workspace / "research.json").read_text())
    assert report["observed_count"] == 1
    assert report["status"] == ("succeeded" if complete else "failed")
    assert report["sources"][0]["url"] == request.source_urls[0]
