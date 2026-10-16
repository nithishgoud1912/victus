"""Real local-fixture M2 adversarial cases; no external sites or normal profiles."""

import argparse
import asyncio
import hashlib
import json
import tempfile
from pathlib import Path

from victus.adapters.playwright.actions import fill_target
from victus.adapters.playwright.locators import TargetResolutionError, TargetResolver
from victus.adapters.playwright.network import NetworkBlocked, NetworkGuard, WebScope
from victus.adapters.playwright.observation import BrowserObserver
from victus.adapters.playwright.session import BrowserSession
from victus.tools.contracts import ActionProposal
from victus.tools.dispatcher import Dispatcher
from victus.tools.registry import ToolRegistry
from victus.workflows.common import Arguments, context_for, spec
from victus.workflows.qualification import FixtureSite


async def cases(origin, executable, data_dir):
    outcomes = []
    allowed = {
        origin + path
        for path in (
            "/controls.html",
            "/source-a.html",
            "/redirect",
            "/escape",
            "/slow.html",
            "/download.html",
        )
    }

    async def run_case(name, operation, scale=1):
        def authorize(request):
            return (
                request.url in allowed
                and request.method == "GET"
                and request.body_sha256 == hashlib.sha256(b"").hexdigest()
            )

        guard = NetworkGuard(
            WebScope(name, frozenset({origin}), private_addresses=frozenset({"127.0.0.1"})),
            authorize=authorize,
        )
        async with BrowserSession(
            network_guard=guard, browser_executable=executable, device_scale_factor=scale
        ) as session:
            ref = await session.new_page()
            page = session._resolve_page(ref)
            resolver = TargetResolver(session, allowed_origins={origin})
            observer = BrowserObserver(resolver)
            actual_scale = await page.evaluate("window.devicePixelRatio")
            await operation(session, ref, page, resolver, observer, guard)
            outcomes.append(
                {
                    "case": name,
                    "status": "passed",
                    "browser_version": session._browser.version,
                    "requested_scale": scale,
                    "actual_device_pixel_ratio": actual_scale,
                }
            )

    async def expect_block(awaitable, code):
        try:
            target = await awaitable
        except TargetResolutionError as error:
            assert str(error) == code, str(error)
        else:
            await target.element.dispose()
            raise AssertionError("Target unexpectedly resolved")

    async def duplicates(session, ref, page, resolver, observer, guard):
        await session.navigate(ref, origin + "/controls.html")
        observed = await observer.observe(ref)
        target = next(t for t in observed.targets if t.label == "Duplicate")
        await expect_block(
            resolver.resolve_target(target.ref, observed.observation_id), "TARGET_NOT_UNIQUE"
        )

    async def stale(session, ref, page, resolver, observer, guard):
        await session.navigate(ref, origin + "/controls.html")
        observed = await observer.observe(ref)
        target = next(t for t in observed.targets if t.label == "Name")
        await page.evaluate("document.querySelector('#name').outerHTML = '<input id=name>'")
        await expect_block(
            resolver.resolve_target(target.ref, observed.observation_id), "OBSERVATION_STALE"
        )

    async def redirects(session, ref, page, resolver, observer, guard):
        await session.navigate(ref, origin + "/redirect")
        assert page.url == origin + "/source-a.html"
        observation = await observer.observe(ref)
        assert "PRIVATE_" not in repr(observation)
        try:
            await session.navigate(ref, origin + "/escape")
        except NetworkBlocked:
            pass
        else:
            raise AssertionError("Metadata redirect was followed")
        assert "ORIGIN_OUTSIDE_SCOPE" in guard.blocked

    async def popups(session, ref, page, resolver, observer, guard):
        await session.navigate(ref, origin + "/controls.html")
        async with page.context.expect_page(timeout=3000) as opened:
            await page.get_by_role("button", name="Open popup", exact=True).click()
        popup = await opened.value
        for _ in range(100):
            if popup.is_closed():
                break
            await asyncio.sleep(0.01)
        assert popup.is_closed()
        assert len(page.context.pages) == 1

    async def downloads(session, ref, page, resolver, observer, guard):
        try:
            await session.navigate(ref, origin + "/download.html")
        except NetworkBlocked:
            pass
        else:
            raise AssertionError("Unreviewed attachment was accepted")
        assert not guard.downloads and "DOWNLOAD_NOT_REVIEWED" in guard.blocked

    async def timeout(session, ref, page, resolver, observer, guard):
        class Empty(Arguments):
            pass

        async def execute(root, args):
            await session.navigate(ref, origin + "/slow.html")
            return {"finished": True}

        registry = ToolRegistry()
        registry.register(
            spec(
                "fixture.slow",
                Empty,
                execute,
                lambda output, args: True,
                "browser:read",
                timeout=0.03,
            )
        )
        root = data_dir / "timeout" / "workspace"
        root.mkdir(parents=True)
        context = context_for(
            root, "timeout-fixture", None, {"browser:read"}, lambda tool, args: True
        )
        outcome = await Dispatcher(root, registry).dispatch_step(
            ActionProposal(tool="fixture.slow", arguments={}), context
        )
        assert outcome.status == "unknown" and not outcome.verified
        assert context.ledger.get(outcome.action_id).status == "unknown"
        await asyncio.sleep(0.5)  # Let the fixture response drain before context shutdown.

    async def windows(session, ref, page, resolver, observer, guard):
        await session.navigate(ref, origin + "/controls.html")
        other = await session.new_page()
        await session.navigate(other, origin + "/controls.html")
        first = await observer.observe(ref)
        second = await observer.observe(other)
        target = next(t for t in first.targets if t.label == "Name")
        await expect_block(
            resolver.resolve_target(target.ref, second.observation_id), "TARGET_UNKNOWN"
        )
        assert await fill_target(resolver, target.ref, first.observation_id, "VICTUS")
        assert (
            await session._resolve_page(other).get_by_label("Name", exact=True).input_value() == ""
        )

    for name, operation in [
        ("duplicate-buttons", duplicates),
        ("stale-fields", stale),
        ("redirects-and-privacy", redirects),
        ("blocked-popup", popups),
        ("download-attempt", downloads),
        ("step-timeout", timeout),
    ]:
        await run_case(name, operation)
    for scale in (1, 1.25, 1.5, 2):
        await run_case(f"multiple-pages-scale-{scale}", windows, scale)
        assert outcomes[-1]["actual_device_pixel_ratio"] == scale
    return outcomes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser-executable", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with (
        tempfile.TemporaryDirectory() as temporary,
        FixtureSite(Path(__file__).parents[1] / "fixtures" / "m2") as site,
    ):
        outcomes = asyncio.run(cases(site.origin, args.browser_executable, Path(temporary)))
    args.output.write_text(
        json.dumps(
            {
                "status": "passed",
                "cases": outcomes,
                "public_sites_qualified": False,
                "windows_native_qualified": False,
            },
            indent=2,
        )
        + "\n"
    )
    print(f"{len(outcomes)} real browser fixture cases passed")


if __name__ == "__main__":
    main()
