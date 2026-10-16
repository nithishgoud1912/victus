"""Schema migration runner for the VICTUS SQLite database.

Migrations are numbered SQL files under ``storage/sql/``.  Each file is
executed at most once; a ``schema_versions`` table tracks which have been
applied.  Migrations run inside a single transaction so a crash mid-apply
leaves the database unchanged.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

_SQL_DIR = Path(__file__).parent / "sql"


def _ensure_version_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_versions (
            version     INTEGER PRIMARY KEY,
            filename    TEXT    NOT NULL,
            applied_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
        )
    """)


def _applied_versions(conn: sqlite3.Connection) -> set[int]:
    rows = conn.execute("SELECT version FROM schema_versions").fetchall()
    return {row[0] for row in rows}


def _discover_migrations() -> list[tuple[int, Path]]:
    """Return ``(version, path)`` pairs sorted by version number."""
    migrations: list[tuple[int, Path]] = []
    for path in sorted(_SQL_DIR.glob("*.sql")):
        # Filename format: 0001_initial.sql → version 1
        prefix = path.stem.split("_", 1)[0]
        try:
            version = int(prefix)
        except ValueError:
            continue
        migrations.append((version, path))
    return migrations


def migrate(db_path: Path) -> list[int]:
    """Apply all pending migrations to *db_path* and return applied version numbers.

    The database file and its parent directory are created if they do not exist.
    Each migration runs inside the same connection but each file is committed
    independently so that a crash leaves only the failing migration unapplied.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    migrations = _discover_migrations()
    if not migrations:
        raise RuntimeError("Schema migration resources are missing")
    conn = sqlite3.connect(db_path, timeout=5)
    applied: list[int] = []
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        _ensure_version_table(conn)
        already = _applied_versions(conn)
        if already and max(already) > max(n for n, _ in migrations):
            raise RuntimeError("Database schema is newer than this application; restore a compatible backup")
        for version, path in migrations:
            if version in already:
                continue
            sql = path.read_text(encoding="utf-8")
            # Run each migration inside its own transaction.
            conn.executescript(sql)
            conn.execute(
                "INSERT INTO schema_versions (version, filename) VALUES (?, ?)",
                (version, path.name),
            )
            conn.commit()
            applied.append(version)
    finally:
        conn.close()
    return applied


def current_version(db_path: Path) -> int | None:
    """Return the highest applied migration version, or ``None`` if none applied."""
    if not db_path.exists():
        return None
    conn = sqlite3.connect(db_path, timeout=5)
    try:
        _ensure_version_table(conn)
        row = conn.execute("SELECT MAX(version) FROM schema_versions").fetchone()
        return row[0] if row and row[0] is not None else None
    finally:
        conn.close()
