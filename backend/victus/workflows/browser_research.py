"""Fixture-first research: observed unique source URLs, extracted text, then artifact."""

from __future__ import annotations

import importlib.metadata
import json
from dataclasses import asdict
from urllib.parse import urlsplit

from pydantic import Field

from victus.adapters.playwright._dom import TEXT_SCRIPT
from victus.adapters.playwright.locators import TargetResolver, origin_of
from victus.adapters.playwright.observation import BrowserObserver
from victus.adapters.playwright.session import PageReference
from victus.workflows.common import (
    Arguments,
    StepFailed,
    WorkflowResult,
    bytes_match,
    digest,
    spec,
    step,
    write_new,
)


class ResearchRequest(Arguments):
    fixture_origin: str
    source_urls: list[str] = Field(min_length=1, max_length=20)
    required_sources: int = Field(ge=1, le=20)
    filename: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}\.json$")
    reviewed_redirect_urls: list[str] = Field(default_factory=list, max_length=20)

    def reviewed_urls(self):
        # M2 qualifies local fixture research only. Public-site support is a separate gate.
        if urlsplit(self.fixture_origin).hostname not in {"127.0.0.1", "::1"}:
            raise PermissionError("M2 research requires an explicitly reviewed loopback fixture")
        approved = frozenset(self.source_urls + self.reviewed_redirect_urls)
        if any(origin_of(url) != origin_of(self.fixture_origin) for url in approved):
            raise PermissionError("Source outside fixture scope")
        if any(urlsplit(url).fragment for url in approved):
            raise PermissionError("Fragments cannot establish distinct fixture sources")
        return approved


class Empty(Arguments):
    pass


class Navigate(Arguments):
    page_id: str
    session_id: str
    url: str


class Observe(Arguments):
    page_id: str
    session_id: str


class Sources(Arguments):
    source_refs: list[str] = Field(max_length=20)


class Publish(Sources):
    filename: str
    summary_ref: str


class BrowserResearchTools:
    def __init__(self, session, request: ResearchRequest, workspace):
        self.session = session
        self.request = request
        self.workspace = workspace
        self.reviewed = request.reviewed_urls()
        self.resolver = TargetResolver(session, allowed_origins={request.fixture_origin})
        self.observer = BrowserObserver(self.resolver)
        self.sources = {}
        self.summaries = {}
        self._outputs = {}
        self.page_ref = None
        self._observed_scale = None

    def register(self, registry):
        for tool in [
            spec(
                "browser.start_research",
                Empty,
                self.start,
                self.verify_start,
                "browser:read",
                timeout=30,
            ),
            spec(
                "browser.navigate_source",
                Navigate,
                self.navigate,
                self.verify_navigation,
                "browser:read",
                timeout=20,
            ),
            spec(
                "browser.observe_source",
                Observe,
                self.observe,
                self.verify_observation,
                "browser:read",
                timeout=20,
            ),
            spec(
                "research.generate_summary",
                Sources,
                self.summarize,
                self.verify_summary,
                "content:generate",
            ),
            spec(
                "research.publish_sources",
                Publish,
                self.publish,
                self.verify_publish,
                "filesystem:save",
            ),
        ]:
            registry.register(tool)

    def authorize(self, tool, args):
        if tool.name == "browser.start_research":
            return True
        if isinstance(args, Navigate):
            return (
                args.url in self.reviewed
                and self.page_ref is not None
                and (args.session_id, args.page_id)
                == (self.page_ref.session_id, self.page_ref.page_id)
            )
        if isinstance(args, Observe):
            return self.page_ref is not None and (args.session_id, args.page_id) == (
                self.page_ref.session_id,
                self.page_ref.page_id,
            )
        if isinstance(args, Sources):
            if any(ref not in self.sources for ref in args.source_refs):
                return False
            return not isinstance(args, Publish) or (
                args.filename == self.request.filename and args.summary_ref in self.summaries
            )
        return False

    async def start(self, workspace, args):
        await self.session.start()
        self.page_ref = await self.session.new_page()
        return asdict(self.page_ref)

    async def verify_start(self, data, args):
        page = self.session._resolve_page(PageReference(**data))
        self._observed_scale = await page.evaluate("window.devicePixelRatio")
        return abs(self._observed_scale - self.session._device_scale_factor) < 0.00001

    async def navigate(self, workspace, args):
        reference = PageReference(args.session_id, args.page_id)
        response = await self.session.navigate(reference, args.url)
        page = self.session._resolve_page(reference)
        return {"url": page.url, "status": response.status if response is not None else 0}

    def verify_navigation(self, data, args):
        page = self.session._resolve_page(PageReference(args.session_id, args.page_id))
        return data["url"] == page.url and page.url in self.reviewed and 200 <= data["status"] < 300

    async def observe(self, workspace, args):
        observation = await self.observer.observe(PageReference(args.session_id, args.page_id))
        return asdict(observation)

    async def verify_observation(self, data, args):
        record = self.resolver._observations.get(data["observation_id"])
        if record is None:
            return False
        page = await self.resolver._assert_fresh(record)
        text = await page.evaluate(TEXT_SCRIPT, {"max_chars": 4000, "max_nodes": 10_000})
        if (
            not text.strip()
            or data["url"] != page.url
            or data["url"] not in self.reviewed
            or data["text"] != text
        ):
            return False
        self.sources[data["observation_id"]] = {
            "url": data["url"],
            "title": data["title"],
            "text": data["text"],
            "observation_id": data["observation_id"],
            "text_sha256": digest(data["text"].encode("utf-8")),
        }
        return True

    def _selected(self, refs):
        # Redirect aliases and repeated observations of one URL count as ONE source.
        unique = {}
        for ref in refs:
            source = self.sources[ref]
            unique.setdefault(source["url"], source)
        return list(unique.values())

    def summarize(self, workspace, args):
        selected = self._selected(args.source_refs)
        summary = " | ".join(source["title"] + ": " + source["text"][:160] for source in selected)
        ref = digest(json.dumps(args.source_refs).encode("utf-8"))
        self.summaries[ref] = (tuple(args.source_refs), summary)
        return {"summary_ref": ref, "summary": summary, "content_generation": True}

    def verify_summary(self, data, args):
        return self.summaries[data["summary_ref"]] == (tuple(args.source_refs), data["summary"])

    def publish(self, workspace, args):
        selected = self._selected(args.source_refs)
        refs, summary = self.summaries[args.summary_ref]
        if refs != tuple(args.source_refs):
            raise PermissionError("Summary is bound to different sources")
        complete = len(selected) >= self.request.required_sources
        report = {
            "kind": "browser_research",
            "status": "succeeded" if complete else "failed",
            "required_sources": self.request.required_sources,
            "observed_count": len(selected),
            "sources": selected,
            "summary": summary,
            "summary_is_content_generation": True,
        }
        report["environment"] = {
            "browser_version": self.session._browser.version,
            "playwright_version": importlib.metadata.version("playwright"),
            "device_scale_factor": self.session._device_scale_factor,
            "observed_device_pixel_ratio": self._observed_scale,
            "explicit_browser_binary": self.session._browser_executable is not None,
        }
        encoded = (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        if len(encoded) > 128_000:
            raise ValueError("Research artifact limit")
        write_new(workspace, args.filename, encoded)
        self._outputs[args.filename] = encoded
        return {
            "filename": args.filename,
            "observed_count": len(selected),
            "required_sources": self.request.required_sources,
            "complete": complete,
            "sha256": digest(encoded),
        }

    def verify_publish(self, data, args):
        # The artifact itself can be verified even when the promised source count was not met.
        # Workflow completion additionally checks `complete` below.
        expected = self._outputs.get(args.filename)
        return expected is not None and bytes_match(self.workspace / args.filename, expected)


async def browser_research(dispatcher, context, request: ResearchRequest) -> WorkflowResult:
    """Generate content only from verified observations; never count a summary as a source."""
    try:
        request.reviewed_urls()
        page = await step(dispatcher, context, "browser.start_research")
        refs = []
        for url in request.source_urls:
            try:
                await step(dispatcher, context, "browser.navigate_source", **page, url=url)
                observation = await step(dispatcher, context, "browser.observe_source", **page)
                refs.append(observation["observation_id"])
            except StepFailed:
                if context.stopped():
                    return WorkflowResult("cancelled", error_code="SERVICE_STOPPED")
        summary = await step(dispatcher, context, "research.generate_summary", source_refs=refs)
        output = await step(
            dispatcher,
            context,
            "research.publish_sources",
            source_refs=refs,
            summary_ref=summary["summary_ref"],
            filename=request.filename,
        )
        return WorkflowResult(
            "succeeded" if output["complete"] else "failed",
            request.filename,
            error_code=None if output["complete"] else "INSUFFICIENT_DISTINCT_SOURCES",
            observed_sources=output["observed_count"],
            actions=tuple(x["action_id"] for x in context.trace),
        )
    except StepFailed as error:
        return WorkflowResult(
            error.outcome.status,
            error_code=error.outcome.error_code,
            actions=tuple(x["action_id"] for x in context.trace),
        )
