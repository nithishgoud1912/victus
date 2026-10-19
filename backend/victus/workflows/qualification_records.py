"""Operator-owned, report-backed qualification. No HTTP input grants authority."""

import hashlib
import json
import os
import re
import sqlite3
import sys
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

HEX = r"[0-9a-f]{64}"
_FROZEN_CACHE = None
NATIVE_CHECKS = frozenset({
    "two_windows", "preexisting_editor", "nonempty_editor", "stale_process",
    "missing_control", "denied_review", "expired_review", "reused_review",
    "changed_payload", "changed_path", "changed_target", "destination_conflict",
    "stop_during_review", "stop_during_save", "restart_invalidation",
    "real_http_review", "real_dashboard_review",
})
BROWSER_CHECKS = frozenset({
    "exact_sources", "redirect_aliases", "replay", "destination_conflict",
    "scope_rejection", "stop_no_later_effect", "owned_cleanup", "missing_binary",
    "timeout", "interrupted_worker", "structured_route", "text_route",
})


def file_hash(path):
    """Reject links/reparse components and bound hashing memory, not file size."""
    path = Path(path).absolute()
    for component in (path, *path.parents):
        stat = component.lstat()
        if component.is_symlink() or getattr(stat, "st_file_attributes", 0) & 0x400:
            raise ValueError("Linked qualification input rejected")
    if not path.is_file():
        raise ValueError("Regular qualification input required")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("Duplicate evidence key")
        value[key] = item
    return value


def read_record(path, *, maximum=8 * 1024 * 1024):
    path = Path(path)
    if path.stat().st_size > maximum:
        raise ValueError("Evidence exceeds bound")
    file_hash(path)
    raw = path.read_bytes()
    if len(raw) > maximum:
        raise ValueError("Evidence exceeds bound")
    def invalid_constant(_):
        raise ValueError("Nonfinite evidence value")
    value = json.loads(raw, object_pairs_hook=_pairs, parse_constant=invalid_constant)
    if not isinstance(value, dict):
        raise ValueError("Evidence object required")
    return value, hashlib.sha256(raw).hexdigest()


def _verify_frozen_files(root, manifest, manifest_hash):
    """Check manifest-bound bytes before granting a frozen capability.

    Recheck file metadata on every call; hash changed files and initially verify
    every file. This is integrity checking, not protection from the same account
    deliberately forging a bundle and its unsigned manifest.
    """
    global _FROZEN_CACHE
    entries = manifest.get("files")
    if not isinstance(entries, list) or not 1 <= len(entries) <= 20000:
        raise ValueError("Frozen file inventory unavailable")
    signature = []
    seen = set()
    for entry in entries:
        name = entry["path"]
        if (not isinstance(name, str) or "\\" in name or ":" in name
                or PurePosixPath(name).is_absolute() or ".." in PurePosixPath(name).parts
                or name in seen or not name or type(entry.get("bytes")) is not int
                or not isinstance(entry.get("sha256"), str)
                or not re.fullmatch(HEX, entry["sha256"])):
            raise ValueError("Malformed frozen inventory")
        seen.add(name)
        path = root.joinpath(*PurePosixPath(name).parts)
        for component in (path, *path.parents):
            status = component.lstat()
            if component.is_symlink() or getattr(status, "st_file_attributes", 0) & 0x400:
                raise ValueError("Linked frozen file rejected")
        status = path.stat()
        if not path.is_file() or status.st_size != entry["bytes"]:
            raise ValueError("Frozen file changed")
        signature.append((name, status.st_size, status.st_mtime_ns, status.st_ctime_ns))
    current = (str(root), manifest_hash, signature)
    if current != _FROZEN_CACHE:
        for entry in entries:
            if file_hash(root.joinpath(*PurePosixPath(entry["path"]).parts)) != entry["sha256"]:
                raise ValueError("Frozen file hash changed")
        _FROZEN_CACHE = current


def runtime_identity():
    """Source Python inventory or exact frozen bundle-manifest identity."""
    if getattr(sys, "frozen", False):
        manifest = Path(sys.executable).with_name("release-manifest.json")
        record, digest = read_record(manifest, maximum=16 * 1024 * 1024)
        if not isinstance(record.get("source_sha256"), str) or not re.fullmatch(HEX, record["source_sha256"]):
            raise ValueError("Frozen source inventory unavailable")
        _verify_frozen_files(manifest.parent, record, digest)
        return hashlib.sha256(b"frozen-v2\0" + digest.encode()).hexdigest()
    root = Path(__file__).resolve().parents[1]
    files = sorted(root.rglob("*.py"))
    if not files:
        raise ValueError("Runtime source inventory unavailable")
    digest = hashlib.sha256(b"source-runtime-v1\0")
    for path in files:
        digest.update(path.relative_to(root).as_posix().encode() + b"\0")
        digest.update(bytes.fromhex(file_hash(path)))
    return digest.hexdigest()


def qualification_path(kind):
    if kind not in {"fixture", "native"}:
        raise ValueError("Unsupported qualification kind")
    configured = os.getenv("VICTUS_QUALIFICATION_DIR")
    if configured:
        root = Path(configured).expanduser()
        if not root.is_absolute():
            raise ValueError("Qualification directory must be absolute")
    elif getattr(sys, "frozen", False):
        local = os.getenv("LOCALAPPDATA")
        if not local:
            raise ValueError("Qualification directory unavailable")
        root = Path(local) / "VICTUS" / "qualifications"
    else:
        # Source compatibility; deployments can explicitly select external storage.
        return Path(__file__).with_name(kind + "-qualification.json")
    return root / runtime_identity() / (kind + "-qualification.json")


def qualified_record(path, kind, checks):
    try:
        record, _ = read_record(path, maximum=65536)
        if (
            type(record.get("schema_version")) is not int or record["schema_version"] != 2
            or record.get("kind") != kind or record.get("qualified") is not True
            or record.get("runtime_sha256") != runtime_identity()
            or type(record.get("verified_runs")) is not int or record["verified_runs"] < 20
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


def _native_profile(record):
    from victus.adapters.uia.applications import load_profiles

    name = record["profile"]
    if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9][a-z0-9.-]{0,95}", name):
        raise ValueError("Invalid native profile")
    root = Path(sys._MEIPASS) if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[3]
    path = root / "config/applications" / (name + ".json")
    if file_hash(path) != record["profiles_sha256"]:
        raise ValueError("Profile changed")
    (profile,) = [item for item in load_profiles(path) if item.name == name]
    if (
        not profile.executable_sha256
        or file_hash(profile.executable) != profile.executable_sha256
        or record["executable_sha256"] != profile.executable_sha256
    ):
        raise ValueError("Native executable changed")
    return NativeAdmission(path, frozenset({name}))


def _physical_dpi(record):
    values = record.get("physical_dpi")
    if (not isinstance(values, list) or any(type(x) is not int or not 72 <= x <= 768 for x in values)
            or len(set(values)) < 2):
        raise ValueError("Two observed physical DPI values required")
    return values


def qualified_native():
    try:
        record = qualified_record(qualification_path("native"), "native", NATIVE_CHECKS)
        if record is None:
            return None
        _physical_dpi(record)
        return _native_profile(record)
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _validate_report(record, kind, checks):
    if (
        type(record.get("schema_version")) is not int or record["schema_version"] != 2
        or record.get("kind") != kind or record.get("qualified") is not True
        or record.get("passed") is not True or record.get("normal_memory_guards") is not True
        or record.get("runtime_sha256") != runtime_identity()
        or record.get("runtime_end_sha256") != runtime_identity()
        or not isinstance(record.get("checks"), dict)
        or not all(record["checks"].get(key) is True for key in checks)
    ):
        raise ValueError("Complete unchanged-runtime evidence required")


def _validate_runs(record, report_path, suffix):
    runs = record.get("runs")
    if (not isinstance(runs, list) or not 20 <= len(runs) <= 1000
            or type(record.get("verified_runs")) is not int or record["verified_runs"] != len(runs)):
        raise ValueError("At least twenty verified runs required")
    seen, tasks, actions = set(), set(), set()
    for run in runs:
        if not isinstance(run, dict):
            raise ValueError("Malformed run")
        name = run.get("destination")
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}" + re.escape(suffix), name):
            raise ValueError("New bounded artifact basename required")
        if name in seen or run.get("verified") is not True:
            raise ValueError("Distinct verified destinations required")
        task, action = run.get("task_id"), run.get("action_id")
        if (not isinstance(task, str) or not re.fullmatch(r"[A-Za-z0-9-]{1,64}", task)
                or not isinstance(action, str) or not re.fullmatch(r"[a-f0-9]{32}", action)
                or task in tasks or action in actions):
            raise ValueError("Distinct task/action receipts required")
        seen.add(name)
        tasks.add(task)
        actions.add(action)
        workspace = report_path.parent / "workspace"
        # Aggregate native sessions refer to retained isolated run roots.
        run_root = report_path.parent
        if "run_root" in run:
            relative = Path(run["run_root"])
            if relative.is_absolute() or relative.drive or ".." in relative.parts:
                raise ValueError("Run root must stay beneath session")
            run_root = report_path.parent / relative
            workspace = run_root / "workspace"
        digest = file_hash(workspace / name)
        if digest != run.get("sha256"):
            raise ValueError("Artifact hash mismatch")
        database = run_root / "victus.sqlite3"
        file_hash(database)
        try:
            with closing(sqlite3.connect(database.absolute().as_uri() + "?mode=ro", uri=True)) as db:
                row = db.execute(
                    "SELECT status,sha256,expected_effect_ref FROM action_attempts WHERE action_id=?",
                    (action,),
                ).fetchone()
        except sqlite3.Error:
            raise ValueError("Retained read-only ledger unavailable") from None
        if row != ("verified", digest, "task:" + task):
            raise ValueError("Verified ledger receipt does not match artifact")
    return runs


def _publish(kind, report, report_hash, fields):
    output = {key: report[key] for key in fields}
    output.update(schema_version=2, kind=kind, qualified=True, report_sha256=report_hash)
    destination = qualification_path(kind)
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Check ancestors too; the final exclusive creation refuses overwrite and links.
    for parent in destination.parents:
        if parent.is_symlink() or getattr(parent.stat(), "st_file_attributes", 0) & 0x400:
            raise ValueError("Linked qualification directory rejected")
    descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(json.dumps(output, indent=2) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
    return destination


def promote_fixture(report_path):
    import importlib.metadata

    from victus.workflows.fixture_research import FIXTURE_HASH

    report_path = Path(report_path).absolute()
    record, digest = read_record(report_path)
    _validate_report(record, "fixture", BROWSER_CHECKS)
    runs = _validate_runs(record, report_path, ".json")
    if (
        record.get("fixture_sha256") != FIXTURE_HASH
        or record.get("playwright_version") != importlib.metadata.version("playwright")
        or {r.get("route") for r in runs} != {"structured", "text"}
        or not all(r.get("owned_cleanup") is True and r.get("replay") is True for r in runs)
    ):
        raise ValueError("Complete fixture identity, routes and cleanup required")
    for run in runs:
        artifact, _ = read_record(report_path.parent / "workspace" / run["destination"])
        sources = artifact.get("sources")
        if (artifact.get("status") != "succeeded" or artifact.get("required_sources") != 2
                or artifact.get("observed_count") != 2 or not isinstance(sources, list)
                or len(sources) != 2):
            raise ValueError("Two distinct observed fixture sources required")
        urls = [urlsplit(source["url"]) for source in sources]
        if ({url.path for url in urls} != {"/source-a.html", "/source-b.html"}
                or len({url.netloc for url in urls}) != 1
                or any(url.scheme != "http" or url.hostname != "127.0.0.1"
                       or url.username or url.password or url.query or url.fragment for url in urls)
                or len({source["observation_id"] for source in sources}) != 2
                or not all(isinstance(source.get("text"), str) and source["text"].strip()
                           and len(source["text"]) <= 4000
                           and hashlib.sha256(source["text"].encode()).hexdigest() == source.get("text_sha256")
                           for source in sources)):
            raise ValueError("Fixture observations do not match their source evidence")
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        executable = Path(pw.chromium.executable_path)
    if file_hash(executable) != record.get("browser_sha256"):
        raise ValueError("Browser changed")
    relative = "/".join(executable.parts[-3:])
    if relative != record.get("browser_relative_path"):
        raise ValueError("Browser location changed")
    return _publish("fixture", record, digest, (
        "runtime_sha256", "fixture_sha256", "playwright_version", "browser_sha256",
        "browser_relative_path", "checks", "verified_runs",
    ))


def promote_native(report_path):
    """Explicit operator maintenance; pending/manual cases never become passes."""
    report_path = Path(report_path).absolute()
    record, digest = read_record(report_path)
    _validate_report(record, "native", NATIVE_CHECKS)
    _validate_runs(record, report_path, ".txt")
    _native_profile(record)
    dpi = set(_physical_dpi(record))
    cases = record.get("case_reports")
    if not isinstance(cases, dict) or set(cases) != NATIVE_CHECKS:
        raise ValueError("Every native case needs a retained report")
    for key, reference in cases.items():
        if not isinstance(reference, dict):
            raise ValueError("Case report reference required")
        relative = Path(reference["file"])
        if relative.is_absolute() or relative.drive or ".." in relative.parts:
            raise ValueError("Case report must stay beneath session")
        case, case_hash = read_record(report_path.parent / relative)
        if (
            type(case.get("schema_version")) is not int or case["schema_version"] != 2
            or case_hash != reference.get("sha256") or case.get("check") != key
            or case.get("passed") is not True or case.get("real_windows") is not True
            or case.get("runtime_sha256") != runtime_identity()
            or case.get("runtime_end_sha256") != runtime_identity()
            or case.get("profile") != record["profile"]
            or case.get("profiles_sha256") != record["profiles_sha256"]
            or case.get("executable_sha256") != record["executable_sha256"]
            or case.get("normal_memory_guards") is not True
        ):
            raise ValueError("Native case report does not match current session")
        evidence = case.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            raise ValueError("Retained native case evidence required")
        for item in evidence:
            relative = Path(item["file"])
            if relative.is_absolute() or relative.drive or ".." in relative.parts:
                raise ValueError("Native case evidence must stay beneath session")
            if file_hash(report_path.parent / relative) != item.get("sha256"):
                raise ValueError("Native case evidence changed")
    observations = record.get("dpi_reports", [])
    measured = set()
    for reference in observations:
        relative = Path(reference["file"])
        if relative.is_absolute() or relative.drive or ".." in relative.parts:
            raise ValueError("DPI report must stay beneath session")
        observation, observed_hash = read_record(report_path.parent / relative)
        if (observed_hash != reference.get("sha256") or observation.get("physical_observed") is not True
                or observation.get("passed") is not True or observation.get("real_windows") is not True
                or observation.get("runtime_sha256") != runtime_identity()
                or observation.get("runtime_end_sha256") != runtime_identity()
                or observation.get("profiles_sha256") != record["profiles_sha256"]
                or observation.get("executable_sha256") != record["executable_sha256"]
                or type(observation.get("dpi")) is not int):
            raise ValueError("Physical DPI evidence required")
        measured.add(observation["dpi"])
    if measured != dpi:
        raise ValueError("Physical DPI coverage mismatch")
    return _publish("native", record, digest, (
        "runtime_sha256", "profile", "profiles_sha256", "executable_sha256",
        "physical_dpi", "checks", "verified_runs",
    ))
