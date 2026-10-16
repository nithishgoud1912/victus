"""Quiescent, WAL-aware SQLite backups with a closed allowlist of retained files."""

import argparse
import hashlib
import json
import sqlite3
import time
from contextlib import closing, contextmanager
from pathlib import Path
from uuid import uuid4

from victus.recovery.resume import ResumeManager
from victus.runtime.instance_lock import InstanceLock
from victus.safety.approvals import ApprovalStore
from victus.storage.action_ledger import ActionLedger
from victus.storage.migrations import _discover_migrations, current_version, migrate
from victus.storage.paths import safe_path


class BackupError(RuntimeError):
    pass


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def sqlite_backup(source, target):
    with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True, timeout=2)) as src:
        with closing(sqlite3.connect(target, timeout=2)) as dst:
            deadline = time.monotonic() + 30

            def progress(*_):
                if time.monotonic() > deadline:
                    raise BackupError("SQLite backup deadline exceeded")

            src.backup(dst, pages=256, progress=progress, sleep=0.02)
            if dst.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise BackupError("SQLite backup integrity check failed")
            dst.execute("PRAGMA journal_mode=DELETE")


def retained_paths(root, db_path):
    result = {}
    with closing(sqlite3.connect(db_path)) as db:
        for relative, expected in db.execute(
            "SELECT relative_path,sha256 FROM evidence_index WHERE expires_at>?", (time.time(),)
        ):
            safe_path(root, relative, prefix="evidence")
            result[relative] = expected
        for name, expected in db.execute(
            "SELECT output_name,sha256 FROM action_attempts WHERE output_name IS NOT NULL AND status='verified'"
        ):
            relative = "workspace/" + name
            safe_path(root, relative, prefix="workspace")
            result[relative] = expected
    return result


class Backups:
    def __init__(self, root, guard):
        self.root, self.guard = root.resolve(), guard

    def create(self, destination):
        destination = Path(destination).absolute()
        if destination.exists() or destination.resolve().is_relative_to(self.root):
            raise BackupError("Choose a new backup directory outside the active data directory")
        if not destination.parent.is_dir():
            raise BackupError("Backup parent directory is unavailable")
        safe_path(destination.parent, destination.name)
        stage = destination.parent / (".victus-backup-" + uuid4().hex)
        stage.mkdir(mode=0o700)
        with self.guard():
            main = safe_path(self.root, "victus.sqlite3")
            if not main.is_file():
                raise BackupError("Source database is unavailable")
            sqlite_backup(main, stage / "victus.sqlite3")
            # Remove executable authority from the copy, never from the live source.
            with closing(sqlite3.connect(stage / "victus.sqlite3")) as db, db:
                db.execute("DELETE FROM approval_permits")
            files = ["victus.sqlite3"]
            checkpoint = safe_path(self.root, "agent/checkpoints.sqlite3")
            if checkpoint.is_file():
                (stage / "agent").mkdir()
                sqlite_backup(checkpoint, stage / "agent/checkpoints.sqlite3")
                files.append("agent/checkpoints.sqlite3")
            retained = retained_paths(self.root, stage / "victus.sqlite3")
            for relative, expected in retained.items():
                source = safe_path(self.root, relative)
                if not source.is_file() or (expected and digest(source) != expected):
                    raise BackupError(
                        "Retained artifact is missing or changed; review before backup"
                    )
                target = safe_path(stage, relative)
                target.parent.mkdir(parents=True, exist_ok=True)
                with source.open("rb") as src, target.open("xb") as dst:
                    for part in iter(lambda: src.read(1024 * 1024), b""):
                        dst.write(part)
                if digest(target) != digest(source):
                    raise BackupError("Artifact changed during backup")
                files.append(relative)
            manifest = {
                "format": 1,
                "schema": current_version(stage / "victus.sqlite3"),
                "checkpoint_schema": 1 if "agent/checkpoints.sqlite3" in files else None,
                "created_at": time.time(),
                "excluded": [
                    "credentials",
                    "browser_sessions",
                    "browser_profiles",
                    "approval_permits",
                    "raw_audio",
                ],
                "files": [
                    {
                        "path": relative,
                        "sha256": digest(stage / relative),
                        "bytes": (stage / relative).stat().st_size,
                    }
                    for relative in sorted(files)
                ],
            }
            (stage / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            if destination.exists():
                raise BackupError("Backup destination already exists")
            for attempt in range(10):
                try:
                    stage.rename(destination)
                    break
                except PermissionError:
                    if attempt == 9 or destination.exists():
                        raise
                    time.sleep(0.05)
        return manifest


def restore(archive, destination):
    archive, destination = Path(archive).absolute(), Path(destination).absolute()
    if destination.exists() or not destination.parent.is_dir():
        raise BackupError("Restore requires a new directory with an available parent")
    safe_path(archive, "manifest.json")
    if (archive / "manifest.json").stat().st_size > 2_000_000:
        raise BackupError("Manifest limit exceeded")
    manifest = json.loads((archive / "manifest.json").read_text(encoding="utf-8"))
    supported = max(n for n, _ in _discover_migrations())
    if (
        manifest.get("format") != 1
        or type(manifest.get("schema")) is not int
        or not 7 <= manifest["schema"] <= supported
    ):
        raise BackupError("Backup schema is not compatible")
    files = manifest.get("files")
    if not isinstance(files, list) or not 1 <= len(files) <= 10000:
        raise BackupError("Invalid backup manifest")
    seen = set()
    for item in files:
        relative = item["path"]
        candidate = safe_path(archive, relative)
        if relative.casefold() in seen:
            raise BackupError("Duplicate backup path")
        seen.add(relative.casefold())
        if relative not in {
            "victus.sqlite3",
            "agent/checkpoints.sqlite3",
        } and not relative.startswith(("workspace/", "evidence/")):
            raise BackupError("Unexpected backup content")
        if (
            not candidate.is_file()
            or candidate.stat().st_size != item["bytes"]
            or digest(candidate) != item["sha256"]
        ):
            raise BackupError("Backup checksum mismatch")
    if "victus.sqlite3" not in seen:
        raise BackupError("Missing main database")
    if current_version(archive / "victus.sqlite3") != manifest["schema"]:
        raise BackupError("Manifest schema does not match database")
    destination.mkdir(mode=0o700)
    lock = InstanceLock(destination)
    lock.acquire()
    try:
        for item in files:
            target = safe_path(destination, item["path"])
            target.parent.mkdir(parents=True, exist_ok=True)
            with safe_path(archive, item["path"]).open("rb") as src, target.open("xb") as dst:
                for chunk in iter(lambda: src.read(1024 * 1024), b""):
                    dst.write(chunk)
            if digest(target) != item["sha256"]:
                raise BackupError("Restored checksum mismatch")
        migrate(destination / "victus.sqlite3")
        checkpoint = destination / "agent/checkpoints.sqlite3"
        if checkpoint.is_file():
            with closing(sqlite3.connect(checkpoint)) as db, db:
                if db.execute("PRAGMA user_version").fetchone()[0] != 1:
                    raise BackupError("Checkpoint schema is not compatible")
                db.execute("UPDATE agent_threads SET cancelled=1")
        ledger = ActionLedger(destination / "victus.sqlite3")
        ResumeManager(ledger, ApprovalStore(ledger.db_path)).recover(quiesced=True)
        with closing(sqlite3.connect(ledger.db_path)) as db, db:
            db.execute("DELETE FROM approval_permits")
            db.execute("DELETE FROM approval_previews")
            for task_id, raw in db.execute("SELECT task_id,result_json FROM tasks").fetchall():
                value = json.loads(raw)
                if value["status"] in {"queued", "prepared", "running"}:
                    value.update(
                        status="unknown", verified=False, error_code="RESTORE_REQUIRES_REVIEW"
                    )
                    db.execute(
                        "UPDATE tasks SET result_json=? WHERE task_id=?",
                        (json.dumps(value), task_id),
                    )
        # Revalidate roots on use; no saved checkpoint can automatically resume a side effect.
        marker = {
            "restored_at": time.time(),
            "requires_path_and_app_revalidation": True,
            "schema": supported,
            "source_manifest_sha256": digest(archive / "manifest.json"),
        }
        (destination / "restore-review.json").write_text(
            json.dumps(marker, indent=2), encoding="utf-8"
        )
        return marker
    except Exception:
        (destination / "RESTORE_FAILED").write_text(
            "Do not activate this incomplete restore.", encoding="utf-8"
        )
        raise
    finally:
        lock.release()


@contextmanager
def offline_guard(root):
    lock = InstanceLock(root)
    lock.acquire()
    agent_lock = None
    try:
        if (root / "agent").is_dir():
            agent_lock = InstanceLock(root / "agent")
            agent_lock.acquire()
        yield
    finally:
        if agent_lock:
            agent_lock.release()
        lock.release()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["create", "restore"])
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "create":
        root = args.source.resolve(strict=True)
        result = Backups(root, lambda: offline_guard(root)).create(args.destination)
    else:
        result = restore(args.source, args.destination)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
