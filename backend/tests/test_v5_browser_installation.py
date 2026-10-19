"""Cache layout and production admission boundaries; no browser is simulated as qualified."""

import importlib.metadata
import json

import pytest

from victus.adapters.playwright import installation
from victus.workflows import fixture_research, qualification_records


@pytest.fixture
def browser_cache(tmp_path, monkeypatch):
    package = tmp_path / "playwright"
    driver = package / "driver/package"
    driver.mkdir(parents=True)
    (driver / "browsers.json").write_text(
        json.dumps({"browsers": [{"name": "chromium", "revision": "1248"}]})
    )
    monkeypatch.setattr(installation.playwright, "__file__", str(package / "__init__.py"))
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(tmp_path / "cache"))
    return tmp_path, driver


def binary(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"synthetic nonexecutable engine identity")
    return path


@pytest.mark.parametrize(
    "platform,tail", [("linux", "chrome-linux64/chrome"), ("win32", "chrome-win64/chrome.exe")]
)
def test_locked_platform_revision_layout_is_resolved(browser_cache, monkeypatch, platform, tail):
    root, _ = browser_cache
    monkeypatch.setattr(installation.sys, "platform", platform)
    target = binary(root / "cache/chromium-1248" / tail)
    assert installation.chromium_executable() == target


def test_linux_default_cache_respects_xdg(browser_cache, monkeypatch):
    root, _ = browser_cache
    monkeypatch.setattr(installation.sys, "platform", "linux")
    monkeypatch.delenv("PLAYWRIGHT_BROWSERS_PATH")
    monkeypatch.setenv("XDG_CACHE_HOME", str(root / "xdg"))
    target = binary(root / "xdg/ms-playwright/chromium-1248/chrome-linux64/chrome")
    assert installation.chromium_executable() == target


def test_windows_default_cache_respects_localappdata(browser_cache, monkeypatch):
    root, _ = browser_cache
    monkeypatch.setattr(installation.sys, "platform", "win32")
    monkeypatch.delenv("PLAYWRIGHT_BROWSERS_PATH")
    monkeypatch.setenv("LOCALAPPDATA", str(root / "local"))
    target = binary(root / "local/ms-playwright/chromium-1248/chrome-win64/chrome.exe")
    assert installation.chromium_executable() == target


def test_hermetic_cache_uses_the_driver_package(browser_cache, monkeypatch):
    _, driver = browser_cache
    monkeypatch.setattr(installation.sys, "platform", "linux")
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", "0")
    target = binary(driver / ".local-browsers/chromium-1248/chrome-linux64/chrome")
    assert installation.chromium_executable() == target


@pytest.mark.parametrize("change", ["revision", "relative", "linked", "missing", "unsupported"])
def test_untrusted_or_unavailable_layout_is_refused(browser_cache, monkeypatch, change):
    root, driver = browser_cache
    monkeypatch.setattr(installation.sys, "platform", "linux")
    target = root / "cache/chromium-1248/chrome-linux64/chrome"
    if change == "revision":
        (driver / "browsers.json").write_text(
            '{"browsers":[{"name":"chromium","revision":"../escape"}]}'
        )
    elif change == "relative":
        monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", "relative")
    elif change == "linked":
        actual = binary(root / "actual")
        target.parent.mkdir(parents=True)
        target.symlink_to(actual)
    elif change == "unsupported":
        monkeypatch.setattr(installation.sys, "platform", "darwin")
    with pytest.raises((ValueError, OSError)):
        installation.chromium_executable()


@pytest.mark.parametrize("change", [None, "hash", "path", "version", "fixture"])
def test_loader_requires_matching_record_and_canonical_engine(browser_cache, monkeypatch, change):
    root, _ = browser_cache
    monkeypatch.setattr(installation.sys, "platform", "linux")
    target = binary(root / "cache/chromium-1248/chrome-linux64/chrome")
    record = {
        "qualified": True,
        "fixture_sha256": fixture_research.FIXTURE_HASH,
        "playwright_version": importlib.metadata.version("playwright"),
        "browser_relative_path": "/".join(target.parts[-3:]),
        "browser_sha256": qualification_records.file_hash(target),
    }
    if change == "hash":
        target.write_bytes(b"changed")
    elif change == "path":
        record["browser_relative_path"] = "../different/chrome"
    elif change == "version":
        record["playwright_version"] = "different"
    elif change == "fixture":
        record["fixture_sha256"] = "0" * 64
    monkeypatch.setattr(fixture_research, "qualified_record", lambda *args: record)
    assert fixture_research.qualified_browser() == (target if change is None else None)
