"""Own Playwright resources inside one worker, thread and asyncio event loop.

Only PageReference values may leave the adapter. Future browser operations must
resolve them inside the owning worker rather than sending Page/Locator over IPC.
"""

from __future__ import annotations

import asyncio
import math
import os
import re
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright

from victus.runtime.instance_lock import InstanceLock

if TYPE_CHECKING:
    from victus.adapters.playwright.network import NetworkGuard


async def _deny_route(route):
    await route.abort("blockedbyclient")


async def _deny_websocket(websocket):
    await websocket.close()


class SessionOwnershipError(RuntimeError):
    """A browser session was accessed outside its owning execution context."""


@dataclass(frozen=True)
class PageReference:
    """Serializable identity, never a live Playwright object or selector."""

    session_id: str
    page_id: str


class BrowserSession:
    """Explicit lifecycle for an owned Chromium browser and isolated context.

    The default context is ephemeral. Supplying both data_dir and profile_name
    explicitly opts into a dedicated persistent profile under VICTUS data.
    No connection to an existing browser or arbitrary user profile is supported.
    Construct and use this class in the browser worker; it is intentionally not
    wired into the synchronous, per-action worker dispatcher yet.
    """

    def __init__(
        self,
        *,
        headless: bool = True,
        channel: str | None = None,
        timeout_ms: float = 30_000,
        data_dir: Path | None = None,
        profile_name: str | None = None,
        network_guard: NetworkGuard | None = None,
    ) -> None:
        if not math.isfinite(timeout_ms) or timeout_ms <= 0:
            raise ValueError("Browser timeout must be positive and finite")
        if channel not in {None, "chromium", "chrome", "msedge"}:
            raise ValueError("Unsupported browser channel")
        if profile_name is not None and (
            data_dir is None or re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", profile_name) is None
        ):
            raise ValueError("Persistent profiles need a data directory and a safe profile name")
        self._headless = headless
        if network_guard is not None and profile_name is not None:
            raise ValueError("Task-scoped network requires an ephemeral context")
        self._network_guard = network_guard
        self._channel = channel
        self._timeout_ms = timeout_ms
        self._data_dir = data_dir
        self._profile_name = profile_name
        self._owner: tuple[int, int, asyncio.AbstractEventLoop] | None = None
        self._lifecycle_lock: asyncio.Lock | None = None
        self._profile_lock: InstanceLock | None = None
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._session_id: str | None = None
        self._pages: dict[str, Page] = {}

    def _check_owner(self) -> None:
        owner = (os.getpid(), threading.get_ident(), asyncio.get_running_loop())
        if self._owner is None:
            self._owner = owner
            self._lifecycle_lock = asyncio.Lock()
        elif self._owner != owner:
            raise SessionOwnershipError(
                "Browser session belongs to another process, thread or loop"
            )

    def __getstate__(self):
        raise TypeError("BrowserSession cannot cross processes; send typed requests and page refs")

    def _prepare_profile(self) -> Path:
        assert self._data_dir is not None and self._profile_name is not None
        root = self._data_dir.expanduser().resolve()
        profiles = root / "browser-profiles"
        profiles.mkdir(parents=True, exist_ok=True)
        if profiles.resolve().parent != root:
            raise ValueError("Browser profile root must remain inside VICTUS data")
        profile = profiles / self._profile_name
        profile.mkdir(exist_ok=True)
        if profile.is_symlink() or profile.resolve().parent != profiles.resolve():
            raise ValueError("Browser profile must be a dedicated VICTUS directory")
        self._profile_lock = InstanceLock(profile)
        self._profile_lock.acquire()
        return profile

    async def start(self) -> None:
        """Launch once; repeated calls on the owning loop are harmless."""
        self._check_owner()
        assert self._lifecycle_lock is not None
        async with self._lifecycle_lock:
            if self._context is not None:
                return
            try:
                profile = self._prepare_profile() if self._profile_name is not None else None
                self._playwright = await async_playwright().start()
                options = {"headless": self._headless, "timeout": self._timeout_ms}
                if self._channel is not None:
                    options["channel"] = self._channel
                if profile is not None:
                    self._context = await self._playwright.chromium.launch_persistent_context(
                        profile, accept_downloads=False, service_workers="block", **options
                    )
                else:
                    self._browser = await self._playwright.chromium.launch(**options)
                    self._context = await self._browser.new_context(
                        accept_downloads=False, service_workers="block"
                    )
                self._context.set_default_timeout(self._timeout_ms)
                self._context.set_default_navigation_timeout(self._timeout_ms)
                if self._network_guard is not None:
                    await self._network_guard.attach(self._context)
                else:
                    await self._context.route("**/*", _deny_route)
                    await self._context.route_web_socket("**/*", _deny_websocket)
                self._session_id = uuid4().hex
            except BaseException:
                # Preserve the startup error even if partially launched resources also fail to close.
                try:
                    await self._close_resources()
                except BaseException:
                    pass
                raise

    async def new_page(self) -> PageReference:
        """Create a page and return only its opaque, session-scoped identity."""
        self._check_owner()
        assert self._lifecycle_lock is not None
        async with self._lifecycle_lock:
            if self._context is None or self._session_id is None:
                raise RuntimeError("Start the browser session before creating pages")
            page = await self._context.new_page()
            page_id = uuid4().hex
            self._pages[page_id] = page
            page.on("close", lambda: self._pages.pop(page_id, None))
            return PageReference(session_id=self._session_id, page_id=page_id)

    def _resolve_page(self, reference: PageReference) -> Page:
        """Adapter-only lookup. Never return this value through a tool or IPC boundary."""
        self._check_owner()
        if self._context is None or reference.session_id != self._session_id:
            raise ValueError("Page reference is stale or belongs to another session")
        page = self._pages.get(reference.page_id)
        if page is None or page.is_closed():
            raise ValueError("Page reference is unknown or closed")
        return page

    async def navigate(self, reference: PageReference, url: str):
        page = self._resolve_page(reference)
        if self._network_guard is None:
            raise ValueError("A task network scope is required for navigation")
        return await self._network_guard.navigate(page, url)

    async def _close_resources(self) -> None:
        self._pages.clear()
        self._session_id = None
        context, self._context = self._context, None
        browser, self._browser = self._browser, None
        playwright, self._playwright = self._playwright, None
        try:
            try:
                if context is not None:
                    await context.close()
            finally:
                try:
                    if browser is not None:
                        await browser.close()
                finally:
                    if playwright is not None:
                        await playwright.stop()
        finally:
            try:
                if self._network_guard is not None:
                    await self._network_guard.close()
            finally:
                if self._profile_lock is not None:
                    self._profile_lock.release()
                    self._profile_lock = None

    async def close(self) -> None:
        """Invalidate references and close only resources launched by this session."""
        self._check_owner()
        assert self._lifecycle_lock is not None
        async with self._lifecycle_lock:
            await self._close_resources()

    async def __aenter__(self) -> BrowserSession:
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        await self.close()
