"""Core database connection manager.

The ``Database`` class provides the shared connection factory and runs
migrations on first initialisation.  The F1 ``tasks`` table is preserved
by migration 0001 and the startup recovery logic still operates on it so
that existing tests remain green.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from victus.storage.migrations import migrate
from victus.tools.contracts import TaskResult


class Database:
    def __init__(self, data_dir: Path) -> None:
        self.path = data_dir / "victus.sqlite3"
        # Run all pending migrations (idempotent).
        migrate(self.path)
        # F1 startup recovery: mark interrupted tasks as unknown.
        with self.connect() as connection:
            # Guard against first-run where the tasks table may be empty.
            for task_id, raw in connection.execute(
                "SELECT task_id, result_json FROM tasks"
            ):
                task = TaskResult.model_validate_json(raw)
                if task.status in {"prepared", "running"}:
                    task.status = "unknown"
                    task.error_code = "RESTART_REQUIRES_REVIEW"
                    connection.execute(
                        "UPDATE tasks SET result_json = ? WHERE task_id = ?",
                        (task.model_dump_json(), task_id),
                    )

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=5)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def save(self, task: TaskResult) -> None:
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO tasks (task_id, result_json) VALUES (?, ?) "
                "ON CONFLICT(task_id) DO UPDATE SET result_json = excluded.result_json",
                (task.task_id, task.model_dump_json()),
            )

    def get(self, task_id: str) -> TaskResult | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT result_json FROM tasks WHERE task_id = ?", (task_id,)
            ).fetchone()
        return TaskResult.model_validate_json(row[0]) if row else None