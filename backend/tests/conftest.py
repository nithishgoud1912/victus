"""Unit tests use controlled telemetry; live qualification uses real host pressure."""

import importlib

import pytest


@pytest.fixture(autouse=True)
def isolated_resources(monkeypatch):
    module = importlib.import_module("victus.runtime.resources")
    supervisor = module.ResourceSupervisor(
        probe=lambda: {
            "available_bytes": 8 * 1024**3,
            "total_bytes": 16 * 1024**3,
            "process_rss_bytes": 64 * 1024**2,
        }
    )
    monkeypatch.setattr(module, "_DEFAULT", supervisor)
    monkeypatch.setattr(module, "gpu_memory", lambda: None)
    try:
        yield supervisor
    finally:
        supervisor.close()
