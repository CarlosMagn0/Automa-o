from __future__ import annotations

import asyncio
import json
import logging
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from database.repository import Repository

log = logging.getLogger(__name__)
LOCAL_TZ = ZoneInfo("America/Sao_Paulo")


@dataclass(frozen=True)
class PageConfig:
    id: str
    name: str
    url: str
    active: bool = True

    def validate(self) -> None:
        parsed = urlparse(self.url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError(f"Invalid URL for {self.id}: use http:// or https://")
        if parsed.username or parsed.password:
            raise ValueError(f"Do not store credentials in the URL for {self.id}")


def load_pages(path: Path) -> list[PageConfig]:
    entries = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(entries, list) or len(entries) > 80:
        raise ValueError("pages_to_open.json must be a list with at most 80 URLs")
    pages = [PageConfig(**entry) for entry in entries]
    ids: set[str] = set()
    urls: set[str] = set()
    for page in pages:
        page.validate()
        if page.id in ids:
            raise ValueError(f"Duplicate page id: {page.id}")
        if page.url in urls:
            raise ValueError(f"Duplicate URL: {page.url}")
        ids.add(page.id)
        urls.add(page.url)
    return pages


class PageOpenerService:
    def __init__(self, pages: list[PageConfig], repository: Repository):
        self.pages = pages
        self.repository = repository
        self.paused = False
        self._lock = asyncio.Lock()
        self.scheduler = AsyncIOScheduler(timezone=LOCAL_TZ)

    def start(self) -> None:
        if self.scheduler.running:
            return
        self.scheduler.add_job(
            self.open_pages,
            IntervalTrigger(hours=2, timezone=LOCAL_TZ),
            id="open_configured_pages",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=300,
        )
        self.scheduler.start()

    def stop(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    async def open_pages(self, force: bool = False) -> dict[str, object]:
        if self.paused and not force:
            return {"status": "paused", "opened": 0, "failed": 0}
        if self._lock.locked():
            return {"status": "already_running", "opened": 0, "failed": 0}

        opened = 0
        failed = 0
        async with self._lock:
            for page in self.pages:
                if not page.active:
                    continue
                run_id = self.repository.start_run(page.id, simulated=False)
                try:
                    ok = await asyncio.to_thread(webbrowser.open, page.url, 0, True)
                    if ok:
                        self.repository.finish_run(run_id, "opened", "Opened in the default browser")
                        opened += 1
                    else:
                        self.repository.finish_run(run_id, "failed", "The default browser did not accept the URL")
                        failed += 1
                except Exception as exc:
                    log.warning("Unable to open page %s (%s)", page.id, type(exc).__name__)
                    self.repository.finish_run(run_id, "failed", f"Open failed: {type(exc).__name__}")
                    failed += 1
        return {"status": "completed", "opened": opened, "failed": failed}

    def pause(self) -> None:
        self.paused = True

    def resume(self) -> None:
        self.paused = False

    def next_run(self) -> str | None:
        job = self.scheduler.get_job("open_configured_pages")
        return job.next_run_time.astimezone(LOCAL_TZ).isoformat() if job and job.next_run_time else None
