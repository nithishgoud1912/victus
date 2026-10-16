"""Task-scoped HTTP mediation. No browser-side DNS lookup or implicit GET permission."""

from __future__ import annotations

import asyncio
import hashlib
import ipaddress
import os
import socket
import threading
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import urljoin, urlsplit

import httpx
from playwright.async_api import Error as PlaywrightError

from victus.adapters.playwright.downloads import TransferBlocked
from victus.adapters.playwright.locators import origin_of
from victus.adapters.playwright.uploads import multipart_files

if TYPE_CHECKING:
    from victus.adapters.playwright.downloads import DownloadStaging
    from victus.adapters.playwright.uploads import UploadReviews


class NetworkBlocked(ValueError):
    """Safe policy code, without request bodies or credentials."""


@dataclass(frozen=True)
class WebScope:
    task_id: str
    origins: frozenset[str]
    private_addresses: frozenset[str] = frozenset()
    allow_popups: bool = False
    allow_downloads: bool = False
    max_response_bytes: int = 10_000_000
    max_request_bytes: int = 10_000_000

    def __post_init__(self):
        if not self.task_id or not 1 <= self.max_response_bytes <= 50_000_000:
            raise ValueError("Invalid web scope limits")
        if not 1 <= self.max_request_bytes <= 50_000_000:
            raise ValueError("Invalid request limit")
        for url in self.origins:
            parsed = urlsplit(url)
            if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
                raise ValueError("Scope requires origins, not URL paths")
        object.__setattr__(self, "origins", frozenset(origin_of(url) for url in self.origins))
        object.__setattr__(
            self,
            "private_addresses",
            frozenset(str(ipaddress.ip_address(ip)) for ip in self.private_addresses),
        )


@dataclass(frozen=True)
class WebRequest:
    task_id: str
    url: str
    method: str
    resource_type: str
    body_sha256: str


async def resolve_addresses(host: str, port: int) -> tuple[str, ...]:
    try:
        return (str(ipaddress.ip_address(host)),)
    except ValueError:
        rows = await asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM)
        return tuple(sorted({row[4][0] for row in rows}))


class NetworkGuard:
    """Install before creating a page. `authorize` is trusted dispatcher policy.

    All HTTP is fetched to a validated numeric IP with original Host/TLS SNI.
    No automatic redirect replay, proxy environment, WebSockets or service workers.
    This is not an OS firewall: do not expose CDP, raw pages or arbitrary browser APIs.
    """

    def __init__(
        self,
        scope: WebScope,
        *,
        authorize: Callable[[WebRequest], bool],
        staging: DownloadStaging | None = None,
        uploads: UploadReviews | None = None,
    ):
        if staging is not None and staging.task_id != scope.task_id:
            raise ValueError("Download staging belongs to another task")
        if uploads is not None and uploads.task_id != scope.task_id:
            raise ValueError("Upload reviews belong to another task")
        self._scope = scope
        self._authorize = authorize
        self._staging = staging
        self._uploads = uploads
        self._context = None
        self._owner = None
        self._closed = False
        self._transport = None
        self._redirects = {}
        self.blocked: deque[str] = deque(maxlen=100)
        self.downloads: deque = deque(maxlen=32)

    @property
    def scope(self) -> WebScope:
        return self._scope

    def _check_owner(self):
        owner = (asyncio.get_running_loop(), os.getpid(), threading.get_ident())
        if self._owner is None:
            self._owner = owner
        if owner != self._owner or self._closed:
            raise NetworkBlocked("NETWORK_SESSION_CLOSED_OR_FOREIGN")

    async def validate_url(self, url: str) -> tuple[str, ...]:
        self._check_owner()
        if len(url) > 8192 or any(ord(c) < 32 for c in url) or "\\" in url:
            raise NetworkBlocked("URL_INVALID")
        try:
            origin = origin_of(url)
            parsed = urlsplit(url)
            host = parsed.hostname.encode("idna").decode("ascii").lower()
            port = (
                parsed.port
                if parsed.port is not None
                else (443 if parsed.scheme == "https" else 80)
            )
        except ValueError:
            raise NetworkBlocked("URL_INVALID") from None
        if origin not in self.scope.origins:
            raise NetworkBlocked("ORIGIN_OUTSIDE_SCOPE")
        if host in {
            "metadata.google.internal",
            "metadata.google",
            "instance-data",
            "instance-data.ec2.internal",
        }:
            raise NetworkBlocked("METADATA_TARGET")
        try:
            async with asyncio.timeout(5):
                addresses = await resolve_addresses(host, port)
        except (OSError, TimeoutError):
            raise NetworkBlocked("DNS_UNAVAILABLE") from None
        if not addresses:
            raise NetworkBlocked("DNS_UNAVAILABLE")
        for address in addresses:
            ip = ipaddress.ip_address(address)
            ip = ip.ipv4_mapped if getattr(ip, "ipv4_mapped", None) else ip
            if (
                ip.is_link_local
                or ip.is_unspecified
                or ip.is_multicast
                or ip.is_reserved
                or str(ip) in {"168.63.129.16", "100.100.100.200", "fd00:ec2::254"}
            ):
                raise NetworkBlocked("METADATA_OR_SPECIAL_ADDRESS")
            if not ip.is_global and str(ip) not in self.scope.private_addresses:
                raise NetworkBlocked("PRIVATE_ADDRESS_NOT_REVIEWED")
        return addresses

    async def attach(self, context):
        self._check_owner()
        if self._context is not None or context.pages:
            raise NetworkBlocked("INSTALL_BEFORE_PAGES")
        self._context = context
        self._transport = httpx.AsyncHTTPTransport(
            trust_env=False, retries=0, limits=httpx.Limits(max_keepalive_connections=0)
        )
        await context.route("**/*", self._route)

        async def deny_websocket(websocket):
            await websocket.close()

        await context.route_web_socket("**/*", deny_websocket)
        context.on("page", self._watch_page)

    def _watch_page(self, page):
        async def check_navigation(frame):
            if (
                frame != page.main_frame
                or frame.url == "about:blank"
                or frame.url.startswith("chrome-error://")
            ):
                return
            try:
                await self.validate_url(frame.url)
            except NetworkBlocked:
                self.blocked.append("NAVIGATION_OUTSIDE_SCOPE")
                await page.close()

        async def cancel_download(download):
            await (
                download.cancel()
            )  # Blob/data/browser-native exports have no reviewed HTTP receipt.
            self.blocked.append("UNREVIEWED_NATIVE_DOWNLOAD")

        async def close_popup():
            if await page.opener() is not None and not self.scope.allow_popups:
                await page.close()

        page.on("framenavigated", check_navigation)
        page.on("download", cancel_download)
        return close_popup()

    async def _fetch(self, url, addresses, method, headers, body):
        original = httpx.URL(url)
        pinned = original.copy_with(host=addresses[0])
        headers = {
            k: v
            for k, v in headers.items()
            if k.lower()
            not in {
                "host",
                "connection",
                "proxy-authorization",
                "transfer-encoding",
                "content-length",
                "accept-encoding",
            }
        }
        headers["host"] = original.netloc.decode("ascii")
        headers["accept-encoding"] = "identity"
        request = httpx.Request(
            method,
            pinned,
            headers=headers,
            content=body,
            extensions={
                "sni_hostname": original.host,
                "timeout": {"connect": 10, "read": 10, "write": 10, "pool": 10},
            },
        )
        response = await self._transport.handle_async_request(request)
        try:
            if len(response.headers.get_list("set-cookie")) > 1:
                raise NetworkBlocked("MULTI_COOKIE_RESPONSE_UNQUALIFIED")
            if response.headers.get("content-encoding", "identity").lower() != "identity":
                raise NetworkBlocked("ENCODED_RESPONSE_UNQUALIFIED")
            data = bytearray()
            async for chunk in response.aiter_raw():
                data.extend(chunk)
                if len(data) > self.scope.max_response_bytes:
                    raise NetworkBlocked("RESPONSE_TOO_LARGE")
            return response.status_code, dict(response.headers), bytes(data)
        finally:
            await response.aclose()

    async def _route(self, route):
        request = route.request
        try:
            self._check_owner()
            addresses = await self.validate_url(request.url)
            page = request.frame.page
            if await page.opener() is not None and not self.scope.allow_popups:
                raise NetworkBlocked("POPUP_NOT_REVIEWED")
            body = request.post_data_buffer or b""
            if len(body) > self.scope.max_request_bytes:
                raise NetworkBlocked("REQUEST_TOO_LARGE")
            proposal = WebRequest(
                self.scope.task_id,
                request.url,
                request.method,
                request.resource_type,
                hashlib.sha256(body).hexdigest(),
            )
            if self._authorize(proposal) is not True:
                raise NetworkBlocked("REQUEST_NOT_AUTHORIZED")
            headers = await request.all_headers()
            content_type = headers.get("content-type", "")
            if content_type.lower().startswith("multipart/form-data"):
                files = multipart_files(content_type, body)
                if files:
                    if self._uploads is None:
                        raise NetworkBlocked("UPLOAD_REVIEW_REQUIRED")
                    self._uploads.authorize_multipart(request.url, files)
            async with asyncio.timeout(20):
                status, headers, data = await self._fetch(
                    request.url, addresses, request.method, headers, body
                )
            if status in {301, 302, 303, 307, 308}:
                target = urljoin(request.url, headers.get("location", ""))
                if not headers.get("location"):
                    raise NetworkBlocked("REDIRECT_MISSING_LOCATION")
                await self.validate_url(target)
                if (
                    request.is_navigation_request()
                    and request.frame == page.main_frame
                    and request.method in {"GET", "HEAD"}
                    and not body
                ):
                    self._redirects[page] = target
                raise NetworkBlocked("REDIRECT_REQUIRES_NAVIGATION")
            disposition = headers.get("content-disposition", "").lower()
            if "attachment" in disposition:
                if not self.scope.allow_downloads or self._staging is None:
                    raise NetworkBlocked("DOWNLOAD_NOT_REVIEWED")
                self.downloads.append(self._staging.stage_bytes(data))
                raise NetworkBlocked("DOWNLOAD_STAGED")
            self._check_owner()
            headers = {
                k: v
                for k, v in headers.items()
                if k.lower()
                not in {
                    "content-length",
                    "transfer-encoding",
                    "connection",
                    "content-encoding",
                }
            }
            await route.fulfill(status=status, headers=headers, body=data)
        except (NetworkBlocked, TransferBlocked, httpx.HTTPError, OSError, TimeoutError) as error:
            self.blocked.append(
                str(error)
                if isinstance(error, (NetworkBlocked, TransferBlocked))
                else "NETWORK_FAILED"
            )
            await route.abort("blockedbyclient")
        except Exception:
            self.blocked.append("NETWORK_POLICY_FAILED")
            await route.abort("blockedbyclient")

    async def navigate(self, page, url: str):
        """Explicit safe GET navigation; each redirect is a fresh authorized request.

        Browser redirect responses are never released unchecked. Subresource,
        form and site-initiated redirects fail closed; a new dispatcher decision
        is required. No request with a body is replayed.
        """
        seen = set()
        for _ in range(6):
            await self.validate_url(url)
            if url in seen:
                raise NetworkBlocked("REDIRECT_LOOP")
            seen.add(url)
            self._redirects.pop(page, None)
            try:
                return await page.goto(url, wait_until="domcontentloaded", timeout=15_000)
            except PlaywrightError:
                target = self._redirects.pop(page, None)
                if target is None:
                    raise NetworkBlocked("NAVIGATION_BLOCKED_OR_UNVERIFIED") from None
                url = target
        raise NetworkBlocked("REDIRECT_LIMIT")

    async def close(self):
        if self._closed:
            return
        self._check_owner()
        self._closed = True
        self._redirects.clear()
        if self._transport is not None:
            await self._transport.aclose()
            self._transport = None
