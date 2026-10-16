"""Explicit real-browser fixture checks. No public site, model or normal profile."""

import asyncio
from dataclasses import asdict
from pathlib import Path

from victus.adapters.playwright.actions import fill_target
from victus.adapters.playwright.locators import TargetResolutionError, TargetResolver
from victus.adapters.playwright.observation import BrowserObserver
from victus.adapters.playwright.session import BrowserSession

ORIGIN = "https://fixture.victus.test"
FIXTURE = Path(__file__).parents[1] / "fixtures" / "browser_observation.html"


async def main() -> None:
    html = FIXTURE.read_text(encoding="utf-8")
    async with BrowserSession() as session:
        page_ref = await session.new_page()
        page = session._resolve_page(page_ref)

        async def fixture_route(route):
            if route.request.url.startswith(ORIGIN + "/"):
                await route.fulfill(body=html, content_type="text/html")
            else:
                await route.abort()

        await page.route("**/*", fixture_route)
        await page.goto(ORIGIN + "/form")
        resolver = TargetResolver(session, allowed_origins={ORIGIN})
        observer = BrowserObserver(resolver, max_text_chars=1000, max_targets=10)

        async def get_target(label):
            observation = await observer.observe(page_ref)
            target = next(target for target in observation.targets if target.label == label)
            return observation, target

        async def blocked(observation, target, code):
            try:
                resolved = await resolver.resolve_target(target.ref, observation.observation_id)
            except TargetResolutionError as error:
                assert str(error) == code, str(error)
            else:
                await resolved.element.dispose()
                raise AssertionError("Expected blocked target")

        observation, target = await get_target("Name")
        assert "PRIVATE_" not in repr(asdict(observation))
        assert observation.title == "VICTUS observation fixture"
        assert len(observation.text) <= 1000
        assert await fill_target(resolver, target.ref, observation.observation_id, "VICTUS")
        assert await page.get_by_label("Name", exact=True).input_value() == "VICTUS"
        await blocked(observation, target, "OBSERVATION_UNKNOWN")

        observation, target = await get_target("Name")
        await page.evaluate("document.querySelector('h1').textContent = 'Changed heading'")
        await blocked(observation, target, "OBSERVATION_STALE")

        observation, target = await get_target("Name")
        await page.evaluate("document.querySelector('#name').outerHTML = '<input id=name>'")
        await blocked(observation, target, "OBSERVATION_STALE")

        await page.evaluate(
            "document.querySelector('button').insertAdjacentHTML('afterend', "
            "'<button>Save</button>')"
        )
        observation, target = await get_target("Save")
        await blocked(observation, target, "TARGET_NOT_UNIQUE")

        observation, target = await get_target("Name")
        await page.goto(ORIGIN + "/next")
        await blocked(observation, target, "OBSERVATION_STALE")
        observation, target = await get_target("Name")
        await page.goto(ORIGIN + "/next")  # Same URL, new document.
        await blocked(observation, target, "OBSERVATION_STALE")

        # A site that overwrites the filled value must not receive verified success.
        await page.evaluate(
            "document.querySelector('#name').addEventListener('input', "
            "event => {event.target.value = 'overwritten';})"
        )
        observation, target = await get_target("Name")
        assert not await fill_target(resolver, target.ref, observation.observation_id, "VICTUS")

        observation, target = await get_target("Name")
        await page.goto("about:blank")
        await blocked(observation, target, "ORIGIN_NOT_ALLOWED")
    print(
        "PASS: privacy, verified fill, mutation/replacement, duplicate, navigation and origin guards"
    )


if __name__ == "__main__":
    asyncio.run(main())
