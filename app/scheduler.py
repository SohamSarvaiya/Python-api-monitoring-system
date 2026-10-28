"""Tiny asyncio scheduler: ticks every second and runs whichever monitors are due."""
import asyncio
import contextlib
import logging
import time
from typing import Optional

from . import checker, db, service
from .config import get_settings

log = logging.getLogger("monitor.scheduler")


class Scheduler:
    def __init__(self) -> None:
        self._task: Optional[asyncio.Task] = None
        self._next_run: dict[int, float] = {}
        self._last_purge = 0.0

    def start(self) -> None:
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

    async def _run(self) -> None:
        async with checker.make_client() as client:
            while True:
                try:
                    await self.tick(client)
                except asyncio.CancelledError:
                    raise
                except Exception:
                    log.exception("scheduler tick failed")
                await asyncio.sleep(1)

    async def tick(self, client) -> int:
        now = time.monotonic()
        monitors = await asyncio.to_thread(db.list_monitors, True)
        due = [m for m in monitors if self._next_run.get(m["id"], 0) <= now]
        for m in due:
            self._next_run[m["id"]] = now + m["interval_seconds"]
        if due:
            results = await asyncio.gather(
                *(service.check_and_record(m, client) for m in due), return_exceptions=True)
            for r in results:
                if isinstance(r, Exception):
                    log.error("check failed unexpectedly: %r", r)
        if now - self._last_purge > 3600:
            self._last_purge = now
            await asyncio.to_thread(db.purge_old_checks, get_settings().retention_days)
        return len(due)
