"""Authenticated SSE with one durable cursor for replay and live delivery."""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator, Callable
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from starlette.responses import StreamingResponse

from victus.tasks.events import EventRecord


async def task_event_stream(
    request: Request, cursor: int, task_id: str | None
) -> AsyncIterator[str]:
    services = request.app.state.services
    events = services.events
    database = services.tasks.database
    # A fixed replay boundary prevents a busy producer from delaying snapshots.
    boundary = await asyncio.to_thread(events.get_latest_event_id)
    highest = cursor
    while True:
        batch = await asyncio.to_thread(events.get_events, highest, task_id, 100, boundary)
        if not batch:
            break
        for event in batch:
            highest = event.event_id
            yield event.to_sse()

    tasks = (
        [await asyncio.to_thread(database.get, task_id)]
        if task_id
        else await asyncio.to_thread(database.list_tasks)
    )
    for task in tasks:
        if task is not None:
            # Snapshots reuse the replay cursor; they do not allocate audit IDs.
            snapshot = EventRecord(
                highest,
                task.task_id,
                "task.snapshot",
                datetime.now(timezone.utc).isoformat(),
                task.model_dump(exclude={"task_id"}),
            )
            yield snapshot.to_sse()

    heartbeat = time.monotonic()
    while not await request.is_disconnected():
        # SQLite is the ordering source even if producers finish out of order.
        batch = await asyncio.to_thread(events.get_events, highest, task_id, 100)
        for event in batch:
            highest = event.event_id
            yield event.to_sse()
        if batch:
            continue
        if time.monotonic() - heartbeat >= 15:
            heartbeat = time.monotonic()
            yield ": ping\n\n"
        await asyncio.sleep(0.05)


def create_events_router(auth_dependency: Callable[..., Any]) -> APIRouter:
    router = APIRouter(tags=["events"])

    @router.get("/api/events", dependencies=[Depends(auth_dependency)])
    async def stream_events(
        request: Request,
        cursor: int | None = Query(default=None, ge=0),
        after: int | None = Query(default=None, ge=0),
        task_id: str | None = Query(default=None),
        last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
    ) -> StreamingResponse:
        resolved = cursor if cursor is not None else after
        if resolved is None:
            try:
                resolved = int(last_event_id) if last_event_id is not None else 0
            except ValueError:
                raise HTTPException(status_code=422, detail="Invalid event cursor") from None
        if resolved < 0:
            raise HTTPException(status_code=422, detail="Invalid event cursor")
        services = request.app.state.services
        if task_id is not None and services.tasks.database.get(task_id) is None:
            raise HTTPException(status_code=404, detail="Task not found")
        if resolved > services.events.get_latest_event_id():
            raise HTTPException(status_code=409, detail="Cursor ahead of event history")
        return StreamingResponse(
            task_event_stream(request, resolved, task_id),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @router.get("/api/tasks/{task_id}/events", dependencies=[Depends(auth_dependency)])
    async def stream_task_events(
        task_id: str,
        request: Request,
        cursor: int | None = Query(default=None, ge=0),
        after: int | None = Query(default=None, ge=0),
        last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
    ) -> StreamingResponse:
        return await stream_events(request, cursor, after, task_id, last_event_id)

    return router
