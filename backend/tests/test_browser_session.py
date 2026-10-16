"""Session lifecycle tests need no browser installation or external website."""

import asyncio
import pickle
from dataclasses import asdict
from unittest.mock import AsyncMock, Mock

import pytest

from victus.adapters.playwright.session import (
    BrowserSession,
    PageReference,
    SessionOwnershipError,
)


@pytest.fixture
def engine(monkeypatch):
    def new_context():
        context = Mock()
        context.close = AsyncMock()
        context.route = AsyncMock()
        context.route_web_socket = AsyncMock()
        context.new_page = AsyncMock(side_effect=lambda: make_page())
        return context

    def make_page():
        page = Mock()
        page.is_closed.return_value = False
        return page

    chromium = Mock()
    contexts = []

    async def context_factory(*args, **kwargs):
        context = new_context()
        contexts.append(context)
        return context

    browser = Mock()
    browser.new_context = AsyncMock(side_effect=context_factory)
    browser.close = AsyncMock()
    chromium.launch = AsyncMock(return_value=browser)
    chromium.launch_persistent_context = AsyncMock(side_effect=context_factory)
    driver = Mock(chromium=chromium)
    driver.stop = AsyncMock()
    manager = Mock()
    manager.start = AsyncMock(return_value=driver)
    factory = Mock(return_value=manager)
    monkeypatch.setattr("victus.adapters.playwright.session.async_playwright", factory)
    return Mock(
        chromium=chromium,
        browser=browser,
        driver=driver,
        manager=manager,
        factory=factory,
        contexts=contexts,
    )


def test_ephemeral_lifecycle_and_opaque_references(engine):
    async def run():
        session = BrowserSession()
        engine.factory.assert_not_called()
        with pytest.raises(RuntimeError, match="Start"):
            await session.new_page()
        await asyncio.gather(session.start(), session.start())
        engine.chromium.launch.assert_awaited_once_with(headless=True, timeout=30_000)
        engine.browser.new_context.assert_awaited_once_with(
            accept_downloads=False, service_workers="block"
        )
        refs = await asyncio.gather(session.new_page(), session.new_page())
        assert refs[0] != refs[1]
        assert all(isinstance(value, str) for value in asdict(refs[0]).values())
        assert pickle.loads(pickle.dumps(refs[0])) == refs[0]
        page = session._resolve_page(refs[0])
        with pytest.raises(ValueError):
            session._resolve_page(PageReference("other", refs[0].page_id))
        page.is_closed.return_value = True
        with pytest.raises(ValueError, match="closed"):
            session._resolve_page(refs[0])
        await session.close()
        await session.close()
        engine.contexts[0].close.assert_awaited_once()
        engine.browser.close.assert_awaited_once()
        engine.driver.stop.assert_awaited_once()
        with pytest.raises(ValueError, match="stale"):
            session._resolve_page(refs[1])
        await session.start()
        assert (await session.new_page()).session_id != refs[0].session_id
        await session.close()

    asyncio.run(run())


def test_fresh_contexts_do_not_share_sessions(engine):
    async def run():
        async with BrowserSession() as first, BrowserSession() as second:
            ref = await first.new_page()
            assert engine.contexts[0] is not engine.contexts[1]
            with pytest.raises(ValueError):
                second._resolve_page(ref)

    asyncio.run(run())


def test_close_event_forgets_page(engine):
    async def run():
        async with BrowserSession() as session:
            ref = await session.new_page()
            page = session._resolve_page(ref)
            event, callback = page.on.call_args.args
            assert event == "close"
            callback()
            with pytest.raises(ValueError, match="unknown"):
                session._resolve_page(ref)

    asyncio.run(run())


def test_ownership_cannot_cross_loops_threads_or_processes(engine, monkeypatch):
    session = BrowserSession()

    async def run():
        await session.start()
        with pytest.raises(SessionOwnershipError):
            await asyncio.to_thread(lambda: asyncio.run(session.new_page()))
        import victus.adapters.playwright.session as module

        pid = module.os.getpid()
        with monkeypatch.context() as patch:
            patch.setattr(module.os, "getpid", lambda: pid + 1)
            with pytest.raises(SessionOwnershipError):
                await session.close()
        with pytest.raises(TypeError, match="cannot cross"):
            pickle.dumps(session)
        await session.close()

    asyncio.run(run())
    with pytest.raises(SessionOwnershipError):
        asyncio.run(session.start())


@pytest.mark.parametrize("stage", ["driver", "launch", "context", "defaults"])
def test_start_failure_closes_partial_resources_and_allows_retry(engine, stage):
    async def run():
        failure = RuntimeError("startup failure")
        failing = {
            "driver": engine.manager.start,
            "launch": engine.chromium.launch,
            "context": engine.browser.new_context,
        }
        original_effects = {name: method.side_effect for name, method in failing.items()}
        session = BrowserSession()
        if stage == "defaults":
            engine.browser.new_context.side_effect = None
            context = Mock()
            context.close = AsyncMock()
            context.route = AsyncMock()
            context.route_web_socket = AsyncMock()
            context.set_default_timeout.side_effect = failure
            engine.browser.new_context.return_value = context
        else:
            failing[stage].side_effect = failure
        with pytest.raises(RuntimeError, match="startup failure"):
            await session.start()
        if stage != "driver":
            engine.driver.stop.assert_awaited_once()
        if stage in {"context", "defaults"}:
            engine.browser.close.assert_awaited_once()
        if stage == "defaults":
            context.close.assert_awaited_once()
            context.set_default_timeout.side_effect = None
        else:
            failing[stage].side_effect = original_effects[stage]
        await session.start()
        await session.close()

    asyncio.run(run())


def test_start_cancellation_cleans_up(engine):
    async def run():
        session = BrowserSession()
        engine.browser.new_context.side_effect = asyncio.CancelledError()
        with pytest.raises(asyncio.CancelledError):
            await session.start()
        engine.browser.close.assert_awaited_once()
        engine.driver.stop.assert_awaited_once()
        await session.close()

    asyncio.run(run())


def test_cleanup_continues_when_context_close_fails(engine):
    async def run():
        session = BrowserSession()
        await session.start()
        engine.contexts[0].close.side_effect = RuntimeError("close failure")
        with pytest.raises(RuntimeError, match="close failure"):
            await session.close()
        engine.browser.close.assert_awaited_once()
        engine.driver.stop.assert_awaited_once()
        await session.close()

    asyncio.run(run())


def test_persistence_is_explicit_and_exclusively_owned(engine, tmp_path):
    async def run():
        first = BrowserSession(data_dir=tmp_path, profile_name="research")
        second = BrowserSession(data_dir=tmp_path, profile_name="research")
        async with first:
            engine.chromium.launch.assert_not_awaited()
            args = engine.chromium.launch_persistent_context.call_args
            assert args.args == (tmp_path / "browser-profiles" / "research",)
            assert args.kwargs["accept_downloads"] is False
            with pytest.raises(RuntimeError, match="owns"):
                await second.start()
            with pytest.raises(RuntimeError, match="owns"):
                await second.start()
        # The profile becomes available only after the owner closes it.
        await second.start()
        await second.close()
        engine.browser.close.assert_not_awaited()

    asyncio.run(run())


def test_persistent_failure_releases_profile_lock(engine, tmp_path):
    async def run():
        first = BrowserSession(data_dir=tmp_path, profile_name="research")
        create_context = engine.chromium.launch_persistent_context.side_effect
        engine.chromium.launch_persistent_context.side_effect = RuntimeError("launch failure")
        with pytest.raises(RuntimeError):
            await first.start()
        engine.chromium.launch_persistent_context.side_effect = create_context
        async with BrowserSession(data_dir=tmp_path, profile_name="research"):
            pass

    asyncio.run(run())


def test_data_dir_alone_does_not_enable_persistence(engine, tmp_path):
    async def run():
        async with BrowserSession(data_dir=tmp_path):
            engine.chromium.launch_persistent_context.assert_not_awaited()
            assert not (tmp_path / "browser-profiles").exists()

    asyncio.run(run())


@pytest.mark.parametrize("name", ["../Default", "Default/profile", "", "..", "UPPER", "a" * 65])
def test_invalid_profile_names(name, tmp_path):
    with pytest.raises(ValueError):
        BrowserSession(data_dir=tmp_path, profile_name=name)


def test_profile_requires_data_directory():
    with pytest.raises(ValueError):
        BrowserSession(profile_name="research")


@pytest.mark.parametrize("timeout", [0, -1, float("inf"), float("nan")])
def test_invalid_timeout(timeout):
    with pytest.raises(ValueError):
        BrowserSession(timeout_ms=timeout)


def test_linked_profile_is_rejected(engine, tmp_path):
    profiles = tmp_path / "data" / "browser-profiles"
    profiles.mkdir(parents=True)
    normal_profile = tmp_path / "normal-browser"
    normal_profile.mkdir()
    try:
        (profiles / "research").symlink_to(normal_profile, target_is_directory=True)
    except OSError:
        pytest.skip("This platform/account cannot create directory symlinks")

    async def run():
        session = BrowserSession(data_dir=tmp_path / "data", profile_name="research")
        with pytest.raises(ValueError, match="dedicated"):
            await session.start()
        engine.factory.assert_not_called()

    asyncio.run(run())


def test_default_session_denies_http_and_websockets(engine):
    async def run():
        async with BrowserSession():
            context = engine.contexts[0]
            route = Mock(abort=AsyncMock())
            await context.route.call_args.args[1](route)
            route.abort.assert_awaited_once_with("blockedbyclient")
            websocket = Mock(close=AsyncMock())
            await context.route_web_socket.call_args.args[1](websocket)
            websocket.close.assert_awaited_once()

    asyncio.run(run())


def test_guard_installed_before_page_creation_and_used_for_navigation(engine):
    async def run():
        guard = Mock(attach=AsyncMock(), close=AsyncMock(), navigate=AsyncMock())
        async with BrowserSession(network_guard=guard) as session:
            guard.attach.assert_awaited_once_with(engine.contexts[0])
            engine.contexts[0].new_page.assert_not_awaited()
            reference = await session.new_page()
            await session.navigate(reference, "https://example.test/")
            guard.navigate.assert_awaited_once_with(
                session._resolve_page(reference), "https://example.test/"
            )
        guard.close.assert_awaited_once()

    asyncio.run(run())


def test_guard_setup_failure_closes_browser_and_guard(engine):
    async def run():
        guard = Mock(attach=AsyncMock(side_effect=RuntimeError("guard setup")), close=AsyncMock())
        with pytest.raises(RuntimeError, match="guard setup"):
            await BrowserSession(network_guard=guard).start()
        engine.contexts[0].close.assert_awaited_once()
        engine.browser.close.assert_awaited_once()
        engine.driver.stop.assert_awaited_once()
        guard.close.assert_awaited_once()

    asyncio.run(run())


def test_task_network_cannot_reuse_persistent_profile(tmp_path):
    with pytest.raises(ValueError, match="ephemeral"):
        BrowserSession(data_dir=tmp_path, profile_name="research", network_guard=Mock())
