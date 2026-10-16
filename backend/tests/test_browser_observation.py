"""Deterministic guard/transport tests; live DOM tests are explicitly invoked."""

import asyncio
import pickle
import time
from dataclasses import asdict
from unittest.mock import AsyncMock, Mock

import pytest

from victus.adapters.playwright._dom import STAMP_SCRIPT, TEXT_SCRIPT
from victus.adapters.playwright.actions import fill_target
from victus.adapters.playwright.locators import (
    TargetResolutionError,
    TargetResolver,
    _ObservationBinding,
    origin_of,
)
from victus.adapters.playwright.observation import (
    BrowserObserver,
    _role_and_label,
)
from victus.adapters.playwright.session import PageReference


@pytest.fixture
def setup():
    identity = {
        "node": 1,
        "tag": "input",
        "type": "text",
        "role": "",
        "id": "name",
        "name": "",
        "href": "",
        "visible": True,
        "sensitive": False,
        "disabled": False,
        "readonly": False,
        "editable": False,
        "hiddenLabel": False,
    }
    stamp = {"document": "doc", "revision": 0, "url": "https://fixture.test/form"}
    session = Mock()
    page = Mock(url=stamp["url"])
    session._resolve_page.return_value = page
    candidate = Mock()
    candidate.evaluate = AsyncMock(side_effect=lambda *a, **kw: dict(identity))
    candidate.aria_snapshot = AsyncMock(return_value='- textbox "Name": old-private-value')
    candidates = Mock()
    candidates.count = AsyncMock(return_value=1)
    candidates.nth.return_value = candidate
    page.locator.return_value = candidates
    page.title = AsyncMock(return_value="Test form")

    def evaluate(script, *args):
        if script == STAMP_SCRIPT:
            return dict(stamp)
        if script == TEXT_SCRIPT:
            return "Visible text"
        raise AssertionError("Unexpected script")

    page.evaluate = AsyncMock(side_effect=evaluate)
    element = Mock()
    element.evaluate = AsyncMock(side_effect=lambda *a: dict(identity))
    element.fill = AsyncMock()
    element.input_value = AsyncMock(return_value="new value")
    element.dispose = AsyncMock()
    locator = Mock()
    locator.count = AsyncMock(return_value=1)
    locator.element_handle = AsyncMock(return_value=element)
    locator.evaluate = AsyncMock(side_effect=lambda *a, **kw: dict(identity))
    page.get_by_role.return_value = locator
    resolver = TargetResolver(session, allowed_origins={"https://fixture.test"})
    return Mock(
        resolver=resolver,
        observer=BrowserObserver(resolver),
        page=page,
        page_ref=PageReference("session", "page"),
        stamp=stamp,
        identity=identity,
        candidate=candidate,
        candidates=candidates,
        locator=locator,
        element=element,
    )


def test_observation_contains_only_serializable_bounded_data(setup):
    async def run():
        observation = await setup.observer.observe(setup.page_ref)
        assert observation.url == setup.page.url
        assert observation.title == "Test form" and observation.text == "Visible text"
        target = observation.targets[0]
        assert target.label == "Name" and target.role == "textbox"
        assert target.operations == ("fill", "read_value")
        assert "old-private-value" not in repr(asdict(observation))
        assert pickle.loads(pickle.dumps(observation)) == observation
        setup.page.get_by_role.assert_called_once_with("textbox", name="Name", exact=True)
        args = [c.args for c in setup.page.evaluate.call_args_list if c.args[0] == TEXT_SCRIPT][0]
        assert args[1] == {"max_chars": 4000, "max_nodes": 10000}

    asyncio.run(run())


@pytest.mark.parametrize(
    "flag,value",
    [
        ("sensitive", True),
        ("visible", False),
        ("disabled", True),
        ("hiddenLabel", True),
        ("readonly", True),
    ],
)
def test_private_hidden_disabled_readonly_targets_omitted(setup, flag, value):
    async def run():
        setup.identity[flag] = value
        observation = await setup.observer.observe(setup.page_ref)
        assert observation.targets == ()
        if flag != "readonly":
            setup.candidate.aria_snapshot.assert_not_awaited()

    asyncio.run(run())


def test_scan_and_target_limits(setup):
    async def run():
        setup.candidates.count.return_value = 100_000
        observer = BrowserObserver(setup.resolver, max_targets=2, max_scan=3, max_text_chars=25)
        result = await observer.observe(setup.page_ref)
        assert len(result.targets) == 2
        assert setup.candidate.aria_snapshot.await_count == 2
        setup.candidate.aria_snapshot.return_value = "- textbox"
        assert not (await observer.observe(setup.page_ref)).targets
        assert setup.candidate.aria_snapshot.await_count == 5

    asyncio.run(run())


def test_verified_fill_is_independent_consumes_observation_and_disposes_node(setup):
    async def run():
        observation = await setup.observer.observe(setup.page_ref)
        assert await fill_target(
            setup.resolver, observation.targets[0].ref, observation.observation_id, "new value"
        )
        setup.element.fill.assert_awaited_once_with("new value", timeout=5000)
        setup.element.input_value.assert_awaited_once_with(timeout=5000)
        setup.element.dispose.assert_awaited_once()
        with pytest.raises(TargetResolutionError, match="OBSERVATION_UNKNOWN"):
            await setup.resolver.resolve_target(
                observation.targets[0].ref, observation.observation_id
            )

    asyncio.run(run())


def test_fill_result_does_not_claim_success_when_value_differs(setup):
    async def run():
        observation = await setup.observer.observe(setup.page_ref)
        setup.element.input_value.return_value = "site replaced the value"
        assert not await fill_target(
            setup.resolver, observation.targets[0].ref, observation.observation_id, "new value"
        )

    asyncio.run(run())


@pytest.mark.parametrize(
    "change,code",
    [
        ("navigation", "OBSERVATION_STALE"),
        ("mutation", "OBSERVATION_STALE"),
        ("document", "OBSERVATION_STALE"),
        ("origin", "ORIGIN_NOT_ALLOWED"),
        ("duplicate", "TARGET_NOT_UNIQUE"),
        ("missing", "TARGET_NOT_UNIQUE"),
        ("identity", "TARGET_IDENTITY_CHANGED"),
        ("expired", "OBSERVATION_EXPIRED"),
    ],
)
def test_write_blocked_on_stale_unsafe_ambiguous_or_changed_target(setup, change, code):
    async def run():
        observation = await setup.observer.observe(setup.page_ref)
        if change == "navigation":
            setup.page.url = "https://fixture.test/other"
            setup.stamp["url"] = setup.page.url
        elif change == "mutation":
            setup.stamp["revision"] += 1
        elif change == "document":
            setup.stamp["document"] = "replacement-document"
        elif change == "origin":
            setup.page.url = "https://elsewhere.test/"
        elif change in {"duplicate", "missing"}:
            setup.locator.count.return_value = 2 if change == "duplicate" else 0
        elif change == "identity":
            setup.identity["node"] += 1
        elif change == "expired":
            setup.resolver._observations[observation.observation_id].created_at = (
                time.monotonic() - 31
            )
        with pytest.raises(TargetResolutionError, match=code):
            await fill_target(
                setup.resolver, observation.targets[0].ref, observation.observation_id, "new value"
            )
        setup.element.fill.assert_not_awaited()

    asyncio.run(run())


def test_reobserve_invalidates_old_references_and_rejects_foreign_refs(setup):
    async def run():
        first = await setup.observer.observe(setup.page_ref)
        second = await setup.observer.observe(setup.page_ref)
        assert first.observation_id != second.observation_id
        assert first.targets[0].ref != second.targets[0].ref
        with pytest.raises(TargetResolutionError, match="OBSERVATION_UNKNOWN"):
            await setup.resolver.resolve_target(first.targets[0].ref, first.observation_id)
        with pytest.raises(TargetResolutionError, match="TARGET_UNKNOWN"):
            await setup.resolver.resolve_target(first.targets[0].ref, second.observation_id)

    asyncio.run(run())


def test_mutation_during_observation_is_not_registered(setup):
    async def run():
        async def mutate():
            setup.stamp["revision"] += 1
            return "Test form"

        setup.page.title.side_effect = mutate
        with pytest.raises(TargetResolutionError, match="OBSERVATION_STALE"):
            await setup.observer.observe(setup.page_ref)
        assert not setup.resolver._observations

    asyncio.run(run())


def test_origin_denied_before_observation_reads_page(setup):
    async def run():
        setup.page.url = "file:///private.html"
        with pytest.raises(TargetResolutionError, match="ORIGIN_NOT_ALLOWED"):
            await setup.observer.observe(setup.page_ref)
        setup.page.evaluate.assert_not_awaited()
        setup.page.title.assert_not_awaited()

    asyncio.run(run())


def test_registry_eviction_is_bounded(setup):
    async def run():
        resolver = TargetResolver(
            setup.resolver._session, allowed_origins=set(), max_observations=1
        )
        empty = _ObservationBinding(PageReference("s", "one"), {}, time.monotonic(), {})
        other = _ObservationBinding(PageReference("s", "two"), {}, time.monotonic(), {})
        resolver._register("one", empty)
        resolver._register("two", other)
        assert list(resolver._observations) == ["two"]

    asyncio.run(run())


@pytest.mark.parametrize(
    "url",
    [
        "file:///tmp/a",
        "data:text/html,x",
        "about:blank",
        "https://user:password@fixture.test",
        "https://fixture.test:99999",
        "https://fixture.test%2f.evil.test",
        "https://fixture.test\\evil",
    ],
)
def test_bad_origins_fail_closed(url):
    with pytest.raises(TargetResolutionError):
        origin_of(url)


def test_origins_normalize_default_ports_and_case():
    assert origin_of("https://FIXTURE.test/path") == origin_of("https://fixture.test:443")
    assert origin_of("http://fixture.test") != origin_of("https://fixture.test")
    assert origin_of("https://fixture.test:444") != origin_of("https://fixture.test")


@pytest.mark.parametrize("snapshot", ["", "- textbox", '- textbox "' + "x" * 257 + '"'])
def test_unlabelled_or_oversized_names_are_not_advertised(snapshot):
    assert _role_and_label(snapshot) is None


def test_last_moment_mutation_blocks_fill_and_disposes_handle(setup):
    async def run():
        observation = await setup.observer.observe(setup.page_ref)

        async def mutate(**kwargs):
            setup.stamp["revision"] += 1
            return setup.element

        setup.locator.element_handle.side_effect = mutate
        with pytest.raises(TargetResolutionError, match="OBSERVATION_STALE"):
            await fill_target(
                setup.resolver, observation.targets[0].ref, observation.observation_id, "new value"
            )
        setup.element.fill.assert_not_awaited()
        setup.element.dispose.assert_awaited_once()

    asyncio.run(run())


def test_verifier_checks_origin_after_fill_before_reading_value(setup):
    async def run():
        observation = await setup.observer.observe(setup.page_ref)

        async def redirect(*args, **kwargs):
            setup.page.url = "https://elsewhere.test/"

        setup.element.fill.side_effect = redirect
        assert not await fill_target(
            setup.resolver, observation.targets[0].ref, observation.observation_id, "new value"
        )
        setup.element.input_value.assert_not_awaited()
        setup.element.dispose.assert_awaited_once()

    asyncio.run(run())


def test_failed_fill_invalidates_observation_and_releases_handle(setup):
    async def run():
        observation = await setup.observer.observe(setup.page_ref)
        setup.element.fill.side_effect = TimeoutError("native write timed out")
        with pytest.raises(TimeoutError):
            await fill_target(
                setup.resolver, observation.targets[0].ref, observation.observation_id, "new value"
            )
        setup.element.input_value.assert_not_awaited()
        setup.element.dispose.assert_awaited_once()
        assert observation.observation_id not in setup.resolver._observations

    asyncio.run(run())


@pytest.mark.parametrize(
    "config",
    [
        {"max_text_chars": 0},
        {"max_text_chars": 16001},
        {"max_targets": 0},
        {"max_targets": 10, "max_scan": 9},
        {"max_scan": 501},
    ],
)
def test_observation_limits_are_validated(setup, config):
    with pytest.raises(ValueError):
        BrowserObserver(setup.resolver, **config)


@pytest.mark.parametrize(
    "config",
    [
        {"max_age_seconds": 0},
        {"max_age_seconds": float("nan")},
        {"max_observations": 0},
    ],
)
def test_resolver_limits_are_validated(setup, config):
    with pytest.raises(ValueError):
        TargetResolver(setup.resolver._session, allowed_origins=set(), **config)


def test_native_error_does_not_expose_typed_text(setup):
    from playwright.async_api import Error as PlaywrightError

    from victus.adapters.playwright.actions import BrowserActionError

    async def run():
        observation = await setup.observer.observe(setup.page_ref)
        setup.element.fill.side_effect = PlaywrightError('fill("PRIVATE_TYPED_TEXT") timed out')
        with pytest.raises(BrowserActionError) as error:
            await fill_target(
                setup.resolver,
                observation.targets[0].ref,
                observation.observation_id,
                "PRIVATE_TYPED_TEXT",
            )
        assert str(error.value) == "BROWSER_FILL_UNCERTAIN"
        assert error.value.__suppress_context__
        assert observation.observation_id not in setup.resolver._observations
        setup.element.dispose.assert_awaited_once()

    asyncio.run(run())
