"""Trusted local qualification records; never populated from API request bodies."""

import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

HEX = r"[0-9a-f]{64}"
NATIVE_CHECKS = frozenset(
    {
        "two_windows",
        "preexisting_editor",
        "nonempty_editor",
        "stale_process",
        "missing_control",
        "denied_review",
        "expired_review",
        "reused_review",
        "changed_payload",
        "changed_path",
        "changed_target",
        "destination_conflict",
        "stop_during_review",
        "stop_during_save",
        "restart_invalidation",
        "real_http_review",
        "real_dashboard_review",
    }
)
BROWSER_CHECKS = frozenset(
    {
        "exact_sources",
        "redirect_aliases",
        "replay",
        "destination_conflict",
        "scope_rejection",
        "stop_no_later_effect",
        "owned_cleanup",
        "missing_binary",
        "timeout",
        "interrupted_worker",
        "structured_route",
        "text_route",
    }
)


def runtime_identity():
    """Bind source runs to runtime Python bytes; frozen runs to their release inventory.

    Source evidence never silently admits a rebuilt folder. Qualification JSON is
    excluded to avoid circular identity when a successfully tested record is installed.
    """
    if getattr(sys, "frozen", False):
        raw = Path(sys.executable).with_name("release-manifest.json").read_bytes()
        record = json.loads(raw)
        digest = record["source_sha256"]
        if not isinstance(digest, str) or not re.fullmatch(HEX, digest):
            raise ValueError("Frozen source inventory unavailable")
        return hashlib.sha256(b"frozen-v1\0" + digest.encode()).hexdigest()
    root = Path(__file__).resolve().parents[1]
    files = sorted(root.rglob("*.py"))
    if not files:
        raise ValueError("Runtime source inventory unavailable")
    digest = hashlib.sha256(b"source-runtime-v1\0")
    for path in files:
        if path.is_symlink():
            raise ValueError("Runtime source link rejected")
        digest.update(path.relative_to(root).as_posix().encode() + b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def qualified_record(path, kind, checks):
    """Return no authority for missing, partial, stale or malformed evidence."""
    try:
        if path.is_symlink() or path.stat().st_size > 65536:
            return None
        record = json.loads(path.read_text(encoding="utf-8"))
        if (
            not isinstance(record, dict)
            or record.get("schema_version") != 1
            or record.get("kind") != kind
            or record.get("qualified") is not True
            or record.get("runtime_sha256") != runtime_identity()
            or type(record.get("verified_runs")) is not int
            or record["verified_runs"] < 20
            or not isinstance(record.get("report_sha256"), str)
            or not re.fullmatch(HEX, record["report_sha256"])
            or not isinstance(record.get("checks"), dict)
            or not all(record["checks"].get(key) is True for key in checks)
        ):
            return None
        return record
    except (OSError, ValueError, KeyError, TypeError):
        return None


@dataclass(frozen=True)
class NativeAdmission:
    profiles_file: Path
    profiles: frozenset[str]


def qualified_native():
    from victus.adapters.uia.applications import load_profiles

    record = qualified_record(
        Path(__file__).with_name("native-qualification.json"), "native", NATIVE_CHECKS
    )
    if record is None:
        return None
    try:
        name = record["profile"]
        if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9][a-z0-9.-]{0,95}", name):
            return None
        root = (
            Path(sys._MEIPASS)
            if getattr(sys, "frozen", False)
            else Path(__file__).resolve().parents[3]
        )
        profiles_file = root / "config/applications" / (name + ".json")
        if (
            profiles_file.is_symlink()
            or hashlib.sha256(profiles_file.read_bytes()).hexdigest() != record["profiles_sha256"]
        ):
            return None
        profiles = load_profiles(profiles_file)
        (profile,) = [p for p in profiles if p.name == name]
        if (
            not profile.executable_sha256
            or profile.executable.is_symlink()
            or hashlib.sha256(profile.executable.read_bytes()).hexdigest()
            != profile.executable_sha256
            or record["executable_sha256"] != profile.executable_sha256
        ):
            return None
        dpi = record["physical_dpi"]
        if (
            not isinstance(dpi, list)
            or len(set(dpi)) < 2
            or any(type(x) is not int or not 72 <= x <= 768 for x in dpi)
        ):
            return None
        return NativeAdmission(profiles_file, frozenset({name}))
    except (OSError, ValueError, KeyError, TypeError):
        return None


def promote_fixture(report_path):
    """Explicit local maintenance only. A public endpoint cannot promote evidence."""
    import importlib.metadata

    from victus.workflows.fixture_research import FIXTURE_HASH

    raw = report_path.read_bytes()
    record = json.loads(raw)
    runs = record.get("runs", [])
    if (
        record.get("kind") != "fixture"
        or record.get("qualified") is not True
        or record.get("passed") is not True
        or record.get("normal_memory_guards") is not True
        or record.get("runtime_sha256") != runtime_identity()
        or record.get("runtime_end_sha256") != runtime_identity()
        or record.get("fixture_sha256") != FIXTURE_HASH
        or record.get("playwright_version") != importlib.metadata.version("playwright")
        or not isinstance(runs, list)
        or len(runs) < 20
        or len({r["destination"] for r in runs}) != len(runs)
        or not all(
            r.get("verified") is True and r.get("owned_cleanup") is True and r.get("replay") is True
            for r in runs
        )
        or record.get("verified_runs") != len(runs)
        or not all(record.get("checks", {}).get(k) is True for k in BROWSER_CHECKS)
    ):
        raise ValueError("Complete unchanged-runtime fixture evidence required")
    allowed = {
        k: record[k]
        for k in (
            "runtime_sha256",
            "fixture_sha256",
            "playwright_version",
            "browser_sha256",
            "browser_relative_path",
            "checks",
            "verified_runs",
        )
    }
    allowed.update(
        schema_version=1,
        kind="fixture",
        qualified=True,
        report_sha256=hashlib.sha256(raw).hexdigest(),
    )
    destination = Path(__file__).with_name("fixture-qualification.json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Never overwrite a historical qualification or follow a link.
    with destination.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(allowed, indent=2) + "\n")
