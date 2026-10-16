"""Task scope, DNS pinning, redirect/request and browser-session policy tests."""

import asyncio
import hashlib
from unittest.mock import AsyncMock, Mock

import httpx
import pytest
from playwright.async_api import Error as PlaywrightError

from victus.adapters.playwright.downloads import DownloadStaging
from victus.adapters.playwright.network import NetworkBlocked, NetworkGuard, WebScope

ORIGIN = "https://example.test"
PUBLIC_IP = "93.184.216.34"


@pytest.fixture
def guard(monkeypatch):
    monkeypatch.setattr(
        "victus.adapters.playwright.network.resolve_addresses", AsyncMock(return_value=(PUBLIC_IP,))
    )
    return NetworkGuard(WebScope("task", frozenset({ORIGIN})), authorize=lambda request: True)


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "data:text/html,x",
        "javascript:alert(1)",
        "https://user:password@example.test/",
        "https://other.test/",
        ORIGIN + "\\private",
        ORIGIN + "\n/path",
        "http://example.test/",
    ],
)
def test_unscoped_or_malformed_urls_are_blocked(guard, url):
    async def run():
        with pytest.raises(NetworkBlocked):
            await guard.validate_url(url)

    asyncio.run(run())


@pytest.mark.parametrize(
    "address",
    [
        "127.0.0.1",
        "10.0.0.1",
        "192.168.1.2",
        "::1",
        "fc00::1",
        "169.254.169.254",
        "168.63.129.16",
        "100.100.100.200",
        "0.0.0.0",
        "224.0.0.1",
        "::ffff:127.0.0.1",
    ],
)
def test_private_metadata_and_special_dns_results_blocked(guard, monkeypatch, address):
    monkeypatch.setattr(
        "victus.adapters.playwright.network.resolve_addresses",
        AsyncMock(return_value=(PUBLIC_IP, address)),
    )

    async def run():
        with pytest.raises(NetworkBlocked):
            await guard.validate_url(ORIGIN)

    asyncio.run(run())


def test_explicit_private_fixture_exception_does_not_allow_metadata(monkeypatch):
    async def run():
        guard = NetworkGuard(
            WebScope(
                "t",
                frozenset({ORIGIN}),
                private_addresses=frozenset({"127.0.0.1", "169.254.169.254"}),
            ),
            authorize=lambda request: True,
        )
        resolver = AsyncMock(return_value=("127.0.0.1",))
        monkeypatch.setattr("victus.adapters.playwright.network.resolve_addresses", resolver)
        assert await guard.validate_url(ORIGIN) == ("127.0.0.1",)
        resolver.return_value = ("169.254.169.254",)
        with pytest.raises(NetworkBlocked, match="METADATA"):
            await guard.validate_url(ORIGIN)

    asyncio.run(run())


def route_for(url=ORIGIN + "/page", method="GET", body=None):
    page = Mock()
    page.opener = AsyncMock(return_value=None)
    page.close = AsyncMock()
    frame = Mock(page=page)
    page.main_frame = frame
    request = Mock(
        url=url, method=method, post_data_buffer=body, resource_type="document", frame=frame
    )
    request.is_navigation_request.return_value = True
    request.all_headers = AsyncMock(return_value={"cookie": "private-cookie"})
    route = Mock(request=request)
    route.abort = AsyncMock()
    route.fulfill = AsyncMock()
    return route, page


def test_get_requires_semantic_authorization_and_digest(guard):
    async def run():
        authorize = Mock(return_value=False)
        guard._authorize = authorize
        guard._fetch = AsyncMock()
        route, _ = route_for(ORIGIN + "/delete-account", body=b"sensitive")
        await guard._route(route)
        guard._fetch.assert_not_awaited()
        route.abort.assert_awaited_once()
        proposal = authorize.call_args.args[0]
        assert proposal.body_sha256 == hashlib.sha256(b"sensitive").hexdigest()
        assert proposal.task_id == "task" and proposal.method == "GET"
        assert guard.blocked[-1] == "REQUEST_NOT_AUTHORIZED"

    asyncio.run(run())


def test_allowed_request_is_fetched_not_continued_by_browser(guard):
    async def run():
        guard._fetch = AsyncMock(return_value=(200, {"content-type": "text/html"}, b"fixture"))
        route, _ = route_for()
        await guard._route(route)
        assert guard._fetch.call_args.args[1] == (PUBLIC_IP,)
        route.fulfill.assert_awaited_once_with(
            status=200, headers={"content-type": "text/html"}, body=b"fixture"
        )
        route.continue_.assert_not_called()

    asyncio.run(run())


@pytest.mark.parametrize(
    "location", ["http://127.0.0.1/", "https://outside.test/", "file:///secret"]
)
def test_redirects_never_escape_scope(guard, location):
    async def run():
        guard._fetch = AsyncMock(return_value=(302, {"location": location}, b""))
        route, _ = route_for()
        await guard._route(route)
        route.fulfill.assert_not_awaited()
        route.abort.assert_awaited_once()
        assert not guard._redirects

    asyncio.run(run())


def test_safe_get_redirect_uses_fresh_explicit_navigation(guard):
    async def run():
        route, page = route_for()
        guard._fetch = AsyncMock(return_value=(302, {"location": "/next"}, b""))
        calls = []

        async def goto(url, **kwargs):
            calls.append(url)
            if len(calls) == 1:
                await guard._route(route)
                raise PlaywrightError("aborted")
            return "verified-response"

        page.goto = AsyncMock(side_effect=goto)
        assert await guard.navigate(page, ORIGIN + "/page") == "verified-response"
        assert calls == [ORIGIN + "/page", ORIGIN + "/next"]
        route.fulfill.assert_not_awaited()

    asyncio.run(run())


def test_post_redirect_never_replays_body(guard):
    async def run():
        guard._fetch = AsyncMock(return_value=(307, {"location": "/next"}, b""))
        route, _ = route_for(method="POST", body=b"private")
        await guard._route(route)
        assert not guard._redirects
        route.abort.assert_awaited_once()

    asyncio.run(run())


def test_popup_first_request_blocked(guard):
    async def run():
        route, page = route_for()
        page.opener.return_value = Mock()
        guard._fetch = AsyncMock()
        await guard._route(route)
        guard._fetch.assert_not_awaited()
        assert guard.blocked[-1] == "POPUP_NOT_REVIEWED"

    asyncio.run(run())


def test_attachment_is_staged_without_destination(guard, tmp_path):
    async def run():
        destination = tmp_path / "output"
        destination.mkdir()
        staging = DownloadStaging(tmp_path, "task", destination_roots=(destination,))
        guard._scope = WebScope("task", frozenset({ORIGIN}), allow_downloads=True)
        guard._staging = staging
        guard._fetch = AsyncMock(
            return_value=(200, {"content-disposition": "attachment; filename=evil.exe"}, b"data")
        )
        route, _ = route_for()
        await guard._route(route)
        assert guard.downloads[0].size == 4
        assert not list(destination.iterdir())
        assert guard.blocked[-1] == "DOWNLOAD_STAGED"
        route.fulfill.assert_not_awaited()

    asyncio.run(run())


class BytesStream(httpx.AsyncByteStream):
    async def __aiter__(self):
        yield b"bounded"


def test_transport_connects_to_ip_and_preserves_tls_hostname_not_proxy(guard):
    async def run():
        guard._transport = Mock()
        guard._transport.handle_async_request = AsyncMock(
            return_value=httpx.Response(
                200, headers={"content-type": "text/plain"}, stream=BytesStream()
            )
        )
        assert (await guard._fetch(ORIGIN + "/page", (PUBLIC_IP,), "GET", {"host": "bad"}, b""))[
            2
        ] == b"bounded"
        request = guard._transport.handle_async_request.call_args.args[0]
        assert request.url.host == PUBLIC_IP
        assert request.headers["host"] == "example.test"
        assert request.extensions["sni_hostname"] == "example.test"

    asyncio.run(run())


def test_install_must_precede_pages_and_closing_disables_guard(guard):
    async def run():
        context = Mock(pages=[])
        context.route = AsyncMock()
        context.route_web_socket = AsyncMock()
        await guard.attach(context)
        context.route.assert_awaited_once()
        context.route_web_socket.assert_awaited_once()
        with pytest.raises(NetworkBlocked, match="INSTALL"):
            await guard.attach(context)
        await guard.close()
        with pytest.raises(NetworkBlocked, match="CLOSED"):
            await guard.validate_url(ORIGIN)

    asyncio.run(run())


def test_real_http_connects_to_validated_ip_ignoring_proxy_environment(monkeypatch):
    async def run():
        captured = []

        async def serve(reader, writer):
            captured.append(await reader.readuntil(b"\r\n\r\n"))
            writer.write(
                b"HTTP/1.1 200 OK\r\nContent-Length: 7\r\nConnection: close\r\n\r\nfixture"
            )
            await writer.drain()
            writer.close()
            await writer.wait_closed()

        server = await asyncio.start_server(serve, "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]
        origin = f"http://fixture.test:{port}"
        guard = NetworkGuard(
            WebScope("t", frozenset({origin}), private_addresses=frozenset({"127.0.0.1"})),
            authorize=lambda request: True,
        )
        monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:1")
        monkeypatch.setattr(
            "victus.adapters.playwright.network.resolve_addresses",
            AsyncMock(return_value=("127.0.0.1",)),
        )
        context = Mock(pages=[])
        context.route = AsyncMock()
        context.route_web_socket = AsyncMock()
        try:
            await guard.attach(context)
            route, _ = route_for(origin + "/page")
            await guard._route(route)
            route.fulfill.assert_awaited_once()
            assert route.fulfill.call_args.kwargs["body"] == b"fixture"
            assert f"host: fixture.test:{port}".encode() in captured[0].lower()
        finally:
            await guard.close()
            server.close()
            await server.wait_closed()

    asyncio.run(run())


def test_multipart_upload_requires_exact_review_even_when_request_policy_allows(guard, tmp_path):
    from victus.adapters.playwright.uploads import UploadReviews

    async def run():
        body = (
            b'--BOUNDARY\r\nContent-Disposition: form-data; name="file"; filename="report.txt"\r\n'
            b"Content-Type: text/plain\r\n\r\nreviewed\r\n--BOUNDARY--\r\n"
        )
        route, _ = route_for(ORIGIN + "/upload", method="POST", body=body)
        route.request.all_headers.return_value = {
            "content-type": "multipart/form-data; boundary=BOUNDARY"
        }
        guard._fetch = AsyncMock(return_value=(200, {}, b"ok"))
        await guard._route(route)
        guard._fetch.assert_not_awaited()
        assert guard.blocked[-1] == "UPLOAD_REVIEW_REQUIRED"
        reviews = UploadReviews("task", source_roots=(tmp_path,))
        guard._uploads = reviews
        reviews._arm(ORIGIN + "/upload", [{"name": "report.txt", "buffer": b"reviewed"}])
        route.request.post_data_buffer = body.replace(b"reviewed", b"substituted")
        await guard._route(route)
        guard._fetch.assert_not_awaited()
        assert guard.blocked[-1] == "UPLOAD_BODY_NOT_REVIEWED"
        route.request.post_data_buffer = body
        await guard._route(route)
        guard._fetch.assert_awaited_once()
        await guard._route(route)  # The body cannot reuse a consumed review.
        guard._fetch.assert_awaited_once()
        assert guard.blocked[-1] == "UPLOAD_BODY_NOT_REVIEWED"

    asyncio.run(run())
