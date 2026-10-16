"""Worker-local target registry and fail-closed resolution before a write."""

from __future__ import annotations

import asyncio
import math
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

from playwright.async_api import ElementHandle, Locator, Page

from victus.adapters.playwright._dom import DESCRIBE_SCRIPT, STAMP_SCRIPT
from victus.adapters.playwright.session import BrowserSession, PageReference

if TYPE_CHECKING:
    from victus.adapters.playwright.observation import ActionableTarget


class TargetResolutionError(ValueError):
    """Safe failure code; contains neither page content nor typed text."""


def origin_of(url: str) -> str:
    """Canonical exact HTTP(S) origin; no wildcards, credentials or opaque URLs."""
    try:
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError
        if parsed.username is not None or parsed.password is not None:
            raise ValueError
        host = parsed.hostname.encode("idna").decode("ascii").lower()
        if any(char in host for char in "%\\\x00 \t\r\n"):
            raise ValueError
        host = f"[{host}]" if ":" in host else host
        port = parsed.port
        if port is None:
            port = 443 if parsed.scheme == "https" else 80
        return f"{parsed.scheme}://{host}:{port}"
    except (ValueError, UnicodeError) as exc:
        raise TargetResolutionError("ORIGIN_NOT_ALLOWED") from exc


@dataclass
class _TargetBinding:
    public: ActionableTarget
    locator: Locator
    identity: dict


@dataclass
class _ObservationBinding:
    page_ref: PageReference
    stamp: dict
    created_at: float
    targets: dict[str, _TargetBinding]


@dataclass
class _ResolvedTarget:
    """Internal pinned node; must never leave the worker/adapter boundary."""

    page: Page
    element: ElementHandle
    binding: _TargetBinding
    observation: _ObservationBinding


class TargetResolver:
    def __init__(
        self,
        session: BrowserSession,
        *,
        allowed_origins: set[str],
        max_age_seconds: float = 30,
        max_observations: int = 32,
    ) -> None:
        if not math.isfinite(max_age_seconds) or max_age_seconds <= 0:
            raise ValueError("Observation lifetime must be positive and finite")
        if not 1 <= max_observations <= 128:
            raise ValueError("Observation capacity must be between 1 and 128")
        for origin in allowed_origins:
            parts = urlsplit(origin)
            if parts.path not in {"", "/"} or parts.query or parts.fragment:
                raise ValueError("Configure origins, not URL paths")
        self._allowed_origins = frozenset(origin_of(url) for url in allowed_origins)
        self._session = session
        self._max_age = max_age_seconds
        self._capacity = max_observations
        self._operation_lock = asyncio.Lock()
        self._observations: OrderedDict[str, _ObservationBinding] = OrderedDict()

    def _check_origin(self, url: str) -> None:
        if origin_of(url) not in self._allowed_origins:
            raise TargetResolutionError("ORIGIN_NOT_ALLOWED")

    def _register(self, observation_id: str, record: _ObservationBinding) -> None:
        self._session._check_owner()
        for key, previous in list(self._observations.items()):
            if previous.page_ref == record.page_ref:
                del self._observations[key]
        self._observations[observation_id] = record
        while len(self._observations) > self._capacity:
            self._observations.popitem(last=False)

    def invalidate(self, observation_id: str) -> None:
        self._session._check_owner()
        self._observations.pop(observation_id, None)

    async def _assert_fresh(self, record: _ObservationBinding) -> Page:
        if not any(current is record for current in self._observations.values()):
            raise TargetResolutionError("OBSERVATION_UNKNOWN")
        page = self._session._resolve_page(record.page_ref)
        self._check_origin(page.url)
        if time.monotonic() - record.created_at > self._max_age:
            raise TargetResolutionError("OBSERVATION_EXPIRED")
        if await page.evaluate(STAMP_SCRIPT) != record.stamp:
            raise TargetResolutionError("OBSERVATION_STALE")
        return page

    async def resolve_target(self, ref: str, observation_id: str) -> _ResolvedTarget:
        """Resolve only inside the worker; caller must dispose the pinned element."""
        self._session._check_owner()
        record = self._observations.get(observation_id)
        if record is None:
            raise TargetResolutionError("OBSERVATION_UNKNOWN")
        binding = record.targets.get(ref)
        if binding is None:
            raise TargetResolutionError("TARGET_UNKNOWN")
        page = await self._assert_fresh(record)
        if await binding.locator.count() != 1:
            raise TargetResolutionError("TARGET_NOT_UNIQUE")
        element = await binding.locator.element_handle(timeout=5000)
        if element is None:
            raise TargetResolutionError("TARGET_MISSING")
        try:
            await self._assert_identity(page, element, binding, record)
            # Close the multi-await validation window before handing back the pinned node.
            await self._assert_fresh(record)
            return _ResolvedTarget(page, element, binding, record)
        except BaseException:
            await element.dispose()
            raise

    async def _assert_identity(
        self,
        page: Page,
        element: ElementHandle,
        binding: _TargetBinding,
        record: _ObservationBinding,
    ) -> None:
        self._check_origin(page.url)
        if page.url != record.stamp["url"]:
            raise TargetResolutionError("OBSERVATION_STALE")
        identity = await element.evaluate(DESCRIBE_SCRIPT)
        if identity != binding.identity:
            raise TargetResolutionError("TARGET_IDENTITY_CHANGED")
        if not identity["visible"] or identity["sensitive"] or identity["disabled"]:
            raise TargetResolutionError("TARGET_NOT_ACTIONABLE")
        if await binding.locator.count() != 1:
            raise TargetResolutionError("TARGET_NOT_UNIQUE")
        # Role/name matching alone cannot distinguish a replacement with the same label.
        if await binding.locator.evaluate(DESCRIBE_SCRIPT, timeout=5000) != identity:
            raise TargetResolutionError("TARGET_IDENTITY_CHANGED")
