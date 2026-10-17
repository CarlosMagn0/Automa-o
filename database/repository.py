from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Repository:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=15)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("""CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                site_id TEXT NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                status TEXT NOT NULL,
                detail TEXT NOT NULL DEFAULT '',
                simulated INTEGER NOT NULL DEFAULT 0
            )""")
            db.execute("CREATE INDEX IF NOT EXISTS idx_runs_site_time ON runs(site_id, started_at DESC)")

    def start_run(self, site_id: str, simulated: bool = False) -> int:
        with self._connect() as db:
            cur = db.execute("INSERT INTO runs(site_id, started_at, status, simulated) VALUES (?, ?, 'running', ?)",
                             (site_id, now_iso(), int(simulated)))
            return int(cur.lastrowid)

    def finish_run(self, run_id: int, status: str, detail: str = "") -> None:
        with self._connect() as db:
            db.execute("UPDATE runs SET finished_at=?, status=?, detail=? WHERE id=?",
                       (now_iso(), status, detail[:500], run_id))

    def history(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute("SELECT * FROM runs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
            return [dict(row) for row in rows]

    def summary(self) -> dict[str, int | str | None]:
        with self._connect() as db:
            total = db.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
            opened = db.execute("SELECT COUNT(*) FROM runs WHERE status='opened'").fetchone()[0]
            failed = db.execute("SELECT COUNT(*) FROM runs WHERE status='failed'").fetchone()[0]
            last = db.execute("SELECT MAX(finished_at) FROM runs").fetchone()[0]
        return {"total_runs": total, "opened": opened, "failures": failed, "last_execution": last}
