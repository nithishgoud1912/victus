"""Bounded, serializable observations; all locators remain in the owning worker."""

from __future__ import annotations

import asyncio
import json
import re
import time
from dataclasses import dataclass
from uuid import uuid4

from victus.adapters.playwright._dom import (
    CANDIDATES,
    DESCRIBE_SCRIPT,
    STAMP_SCRIPT,
    TEXT_SCRIPT,
)
from victus.adapters.playwright.locators import (
    TargetResolutionError,
    TargetResolver,
    _ObservationBinding,
    _TargetBinding,
)
from victus.adapters.playwright.session import PageReference


@dataclass(frozen=True)
class ActionableTarget:
    ref: str
    role: str
    label: str
    operations: tuple[str, ...]


@dataclass(frozen=True)
class Observation:
    observation_id: str
    url: str
    title: str
    text: str
    targets: tuple[ActionableTarget, ...]


# Parse only the header, never the value or child content of an ARIA snapshot.
_ARIA_HEADER = re.compile(r'^- ([a-z]+)(?: ("(?:[^"\\]|\\.)*"))?')


def _role_and_label(snapshot: str) -> tuple[str, str] | None:
    first = snapshot.partition("\n")[0]
    if len(first) > 2048:
        return None
    match = _ARIA_HEADER.match(first)
    if match is None or match[2] is None:
        return None
    try:
        label = json.loads(match[2])
    except (ValueError, TypeError):
        return None
    if not isinstance(label, str) or not 1 <= len(label) <= 256:
        return None
    return match[1], label


def _operations(role: str, identity: dict) -> tuple[str, ...]:
    if role in {"textbox", "searchbox", "spinbutton"}:
        if identity["tag"] not in {"input", "textarea"}:
            return ()  # Custom/contenteditable widgets require separate qualification.
        if identity["readonly"]:
            return ()
        if identity["tag"] == "input" and identity["type"] not in {
            "text",
            "email",
            "url",
            "tel",
            "search",
            "number",
        }:
            return ()
        return ("fill", "read_value")
    return {
        "button": ("click",),
        "link": ("click",),
        "checkbox": ("check", "uncheck"),
        "radio": ("check",),
        "combobox": ("select_option",) if identity["tag"] == "select" else (),
    }.get(role, ())


class BrowserObserver:
    def __init__(
        self,
        resolver: TargetResolver,
        *,
        max_text_chars: int = 4000,
        max_targets: int = 40,
        max_scan: int = 200,
    ) -> None:
        if not 1 <= max_text_chars <= 16_000:
            raise ValueError("Text limit must be between 1 and 16000")
        if not 1 <= max_targets <= max_scan <= 500:
            raise ValueError("Require 1 <= target limit <= scan limit <= 500")
        self._resolver = resolver
        self._text_limit = max_text_chars
        self._target_limit = max_targets
        self._scan_limit = max_scan

    async def observe(self, page_ref: PageReference) -> Observation:
        """Observe only an allowed origin; page instability fails closed."""
        self._resolver._session._check_owner()
        async with asyncio.timeout(15):
            async with self._resolver._operation_lock:
                return await self._observe(page_ref)

    async def _observe(self, page_ref: PageReference) -> Observation:
        resolver = self._resolver
        page = resolver._session._resolve_page(page_ref)
        resolver._check_origin(page.url)
        created_at = time.monotonic()
        stamp = await page.evaluate(STAMP_SCRIPT)
        resolver._check_origin(stamp["url"])
        if len(stamp["url"]) > 2048:
            raise TargetResolutionError("URL_TOO_LONG")
        title = (await page.title())[:512]
        text = await page.evaluate(
            TEXT_SCRIPT, {"max_chars": self._text_limit, "max_nodes": 10_000}
        )
        bindings = {}
        candidates = page.locator(CANDIDATES)
        for index in range(min(await candidates.count(), self._scan_limit)):
            candidate = candidates.nth(index)
            identity = await candidate.evaluate(DESCRIBE_SCRIPT, timeout=5000)
            if (
                not identity["visible"]
                or identity["sensitive"]
                or identity["disabled"]
                or identity["hiddenLabel"]
            ):
                continue
            semantic = _role_and_label(await candidate.aria_snapshot(timeout=5000))
            if semantic is None:
                continue
            role, label = semantic
            operations = _operations(role, identity)
            if not operations:
                continue
            target = ActionableTarget(uuid4().hex, role, label, operations)
            # Exact role/name locators are rechecked for uniqueness at dispatch.
            locator = page.get_by_role(role, name=label, exact=True)
            bindings[target.ref] = _TargetBinding(target, locator, identity)
            if len(bindings) >= self._target_limit:
                break
        resolver._check_origin(page.url)
        if await page.evaluate(STAMP_SCRIPT) != stamp:
            raise TargetResolutionError("OBSERVATION_STALE")
        observation_id = uuid4().hex
        resolver._register(
            observation_id, _ObservationBinding(page_ref, stamp, created_at, bindings)
        )
        return Observation(
            observation_id,
            stamp["url"],
            title,
            text,
            tuple(binding.public for binding in bindings.values()),
        )
