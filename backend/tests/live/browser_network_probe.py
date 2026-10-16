"""Explicit real Chromium + isolated loopback HTTP qualification for 6C."""

import asyncio
import hashlib
import tempfile
from pathlib import Path

from victus.adapters.playwright.downloads import DownloadStaging
from victus.adapters.playwright.network import NetworkBlocked, NetworkGuard, WebScope
from victus.adapters.playwright.session import BrowserSession


async def main():
    hits = []

    async def serve(reader, writer):
        request = await reader.readuntil(b"\r\n\r\n")
        path = request.split(b" ")[1].decode("ascii")
        hits.append(path)
        status, extra, body = "200 OK", "", b"<html><title>Fixture</title>Allowed fixture</html>"
        if path == "/redirect":
            status, extra, body = "302 Found", "Location: /page\r\n", b""
        elif path == "/escape":
            status, extra, body = "302 Found", "Location: http://169.254.169.254/\r\n", b""
        elif path == "/download":
            extra, body = (
                "Content-Disposition: attachment; filename=ignored.txt\r\n",
                b"fixture bytes",
            )
        response = (
            f"HTTP/1.1 {status}\r\n{extra}Content-Length: {len(body)}\r\nConnection: close\r\n\r\n"
        )
        writer.write(response.encode("ascii") + body)
        await writer.drain()
        writer.close()
        await writer.wait_closed()

    server = await asyncio.start_server(serve, "127.0.0.1", 0)
    origin = f"http://127.0.0.1:{server.sockets[0].getsockname()[1]}"
    try:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "output"
            output.mkdir()
            staging = DownloadStaging(root, "fixture-task", destination_roots=(output,))
            reviewed = {origin + path for path in ("/page", "/redirect", "/escape", "/download")}
            empty_digest = hashlib.sha256(b"").hexdigest()

            def authorize(request):
                return (
                    request.url in reviewed
                    and request.method == "GET"
                    and request.body_sha256 == empty_digest
                )

            guard = NetworkGuard(
                WebScope(
                    "fixture-task",
                    frozenset({origin}),
                    private_addresses=frozenset({"127.0.0.1"}),
                    allow_downloads=True,
                ),
                authorize=authorize,
                staging=staging,
            )
            async with BrowserSession(network_guard=guard) as session:
                ref = await session.new_page()
                await session.navigate(ref, origin + "/redirect")
                page = session._resolve_page(ref)
                assert page.url == origin + "/page"
                await page.evaluate("fetch('/delete').catch(() => null)")
                assert "/delete" not in hits  # GET alone did not grant permission.
                try:
                    await session.navigate(ref, origin + "/escape")
                except NetworkBlocked:
                    pass
                else:
                    raise AssertionError("Metadata redirect was accepted")
                try:
                    await session.navigate(ref, origin + "/download")
                except NetworkBlocked:
                    pass
                receipt = guard.downloads[0]
                assert not list(output.iterdir())
                permit = staging.approve_release(receipt, output / "fixture.txt")
                assert staging.release(permit).read_bytes() == b"fixture bytes"
                assert "ORIGIN_OUTSIDE_SCOPE" in guard.blocked
        print("PASS: real browser redirect, request denial, metadata guard and staged release")
    finally:
        server.close()
        await server.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())
