"""Explicit readiness must sample actual configured telemetry, never an empty cache."""

import pytest

from victus.runtime.resources import ResourcePressure, ResourceSupervisor


def test_preflight_samples_before_accepting_empty_cache_and_preserves_threshold():
    supervisor = ResourceSupervisor(probe=lambda: {"available_bytes": 2 * 1024**3 - 1})
    with pytest.raises(ResourcePressure, match="LOCAL_RESOURCE_PRESSURE"):
        supervisor.check_current()
    assert supervisor.min_available == 2 * 1024**3


def test_live_sample_overrides_stale_ready_cache():
    samples = iter([{"available_bytes": 8 * 1024**3}, {"available_bytes": 1024**3}])
    supervisor = ResourceSupervisor(probe=lambda: next(samples))
    assert supervisor.check_current()["available_bytes"] == 8 * 1024**3
    with pytest.raises(ResourcePressure, match="LOCAL_RESOURCE_PRESSURE"):
        supervisor.check_current()


@pytest.mark.parametrize("sample", [{}, {"available_bytes": None}, {"available_bytes": True},
                                     {"available_bytes": 0}, {"available_bytes": "8000000000"}])
def test_unknown_or_malformed_telemetry_cannot_establish_readiness(sample):
    with pytest.raises(ResourcePressure, match="LOCAL_RESOURCE_TELEMETRY_UNAVAILABLE"):
        ResourceSupervisor(probe=lambda: sample).check_current()


def test_probe_error_is_sanitized_and_does_not_create_a_background_owner():
    def probe():
        raise OSError("SECRET")

    supervisor = ResourceSupervisor(probe=probe)
    with pytest.raises(ResourcePressure, match="LOCAL_RESOURCE_TELEMETRY_UNAVAILABLE") as result:
        supervisor.check_current()
    assert "SECRET" not in str(result.value)
    assert supervisor._thread is None and supervisor._users == 0
