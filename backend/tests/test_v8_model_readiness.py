"""Provider-schema readiness only; no installed model or live inference proof."""

import httpx
import pytest

from victus.models.contracts import ModelPin
from victus.models.ollama import installed_pin_available

PIN = ModelPin(name="candidate:4b", digest="sha256:" + "a" * 64)


@pytest.mark.parametrize("digest", ["a" * 64, "sha256:" + "a" * 64])
def test_unique_exact_installed_pin_is_available(digest):
    seen = []

    def handler(request):
        seen.append((str(request.url), request.method))
        return httpx.Response(200, json={"models": [{"name": PIN.name, "digest": digest}]})

    assert installed_pin_available(PIN, transport=httpx.MockTransport(handler))
    assert seen == [("http://127.0.0.1:11434/api/tags", "GET")]


@pytest.mark.parametrize(
    "models",
    [
        [None],
        ["private provider data"],
        {},
        [{"name": PIN.name, "digest": "b" * 64}],
        [{"name": PIN.name, "digest": "a" * 64}] * 2,
        [{"name": PIN.name, "digest": 1}],
        [{"name": PIN.name, "digest": "a" * 64}] * 257,
    ],
)
def test_malformed_duplicate_or_drifted_tags_never_establish_readiness(models):
    assert not installed_pin_available(
        PIN, transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"models": models}))
    )


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(302, headers={"Location": "https://external.invalid/"}),
        httpx.Response(500),
        httpx.Response(200, content=b"{"),
        httpx.Response(200, content=b"x" * 200001),
        httpx.Response(200, content=b'{"models":[],"models":[]}'),
    ],
)
def test_bounded_non_redirecting_readiness_fails_closed(response):
    assert not installed_pin_available(PIN, transport=httpx.MockTransport(lambda _: response))


def test_no_pin_makes_no_request():
    def forbidden(_):
        raise AssertionError("Readiness must not start an unselected model")

    assert not installed_pin_available(None, transport=httpx.MockTransport(forbidden))
