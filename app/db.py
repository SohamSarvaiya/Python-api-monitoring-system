"""SQLite storage. Plain sqlite3 keeps the project dependency-light; the small
function surface below is the only place SQL lives, so swapping to PostgreSQL
means re-implementing just this module."""
import contextlib
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Optional

from .config import get_settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS monitors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    url TEXT NOT NULL,
    method TEXT NOT NULL DEFAULT 'GET',
    interval_seconds INTEGER NOT NULL DEFAULT 60,
    timeout_seconds INTEGER NOT NULL DEFAULT 10,
    expected_status INTEGER,
    enabled INTEGER NOT NULL DEFAULT 1,
    state TEXT NOT NULL DEFAULT 'unknown',
    consecutive_failures INTEGER NOT NULL DEFAULT 0,
    last_checked_at TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    monitor_id INTEGER NOT NULL REFERENCES monitors(id) ON DELETE CASCADE,
    checked_at TEXT NOT NULL,
    status_code INTEGER,
    response_ms REAL,
    ok INTEGER NOT NULL,
    error TEXT
);
CREATE INDEX IF NOT EXISTS idx_checks_monitor_time ON checks(monitor_id, checked_at);
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    monitor_id INTEGER NOT NULL REFERENCES monitors(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat()


@contextlib.contextmanager
def connect():
    path = get_settings().db_path
    if path != ":memory:":
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with connect() as c:
        c.executescript(SCHEMA)
        c.execute("PRAGMA journal_mode=WAL")


def _row(r: Optional[sqlite3.Row]) -> Optional[dict]:
    if r is None:
        return None
    d = dict(r)
    if "enabled" in d:
        d["enabled"] = bool(d["enabled"])
    if "ok" in d:
        d["ok"] = bool(d["ok"])
    return d


# ---------- monitors ----------
def create_monitor(name: str, url: str, method: str = "GET", interval_seconds: int = 60,
                   timeout_seconds: int = 10, expected_status: Optional[int] = None,
                   enabled: bool = True) -> dict:
    with connect() as c:
        cur = c.execute(
            "INSERT INTO monitors(name,url,method,interval_seconds,timeout_seconds,"
            "expected_status,enabled,created_at) VALUES (?,?,?,?,?,?,?,?)",
            (name, url, method, interval_seconds, timeout_seconds, expected_status,
             int(enabled), iso(utcnow())),
        )
        return _row(c.execute("SELECT * FROM monitors WHERE id=?", (cur.lastrowid,)).fetchone())


def list_monitors(only_enabled: bool = False) -> list[dict]:
    q = "SELECT * FROM monitors" + (" WHERE enabled=1" if only_enabled else "") + " ORDER BY id"
    with connect() as c:
        return [_row(r) for r in c.execute(q).fetchall()]


def get_monitor(monitor_id: int) -> Optional[dict]:
    with connect() as c:
        return _row(c.execute("SELECT * FROM monitors WHERE id=?", (monitor_id,)).fetchone())


def delete_monitor(monitor_id: int) -> bool:
    with connect() as c:
        return c.execute("DELETE FROM monitors WHERE id=?", (monitor_id,)).rowcount > 0


def set_enabled(monitor_id: int, enabled: bool) -> Optional[dict]:
    with connect() as c:
        c.execute("UPDATE monitors SET enabled=? WHERE id=?", (int(enabled), monitor_id))
    return get_monitor(monitor_id)


def update_monitor_state(monitor_id: int, state: str, failures: int, checked_at: str) -> None:
    with connect() as c:
        c.execute(
            "UPDATE monitors SET state=?, consecutive_failures=?, last_checked_at=? WHERE id=?",
            (state, failures, checked_at, monitor_id),
        )


# ---------- checks ----------
def insert_check(monitor_id: int, checked_at: str, status_code: Optional[int],
                 response_ms: Optional[float], ok: bool, error: Optional[str]) -> None:
    with connect() as c:
        c.execute(
            "INSERT INTO checks(monitor_id,checked_at,status_code,response_ms,ok,error) "
            "VALUES (?,?,?,?,?,?)",
            (monitor_id, checked_at, status_code, response_ms, int(ok), error),
        )


def get_checks(monitor_id: int, since: Optional[str] = None, limit: Optional[int] = None,
               newest_first: bool = False) -> list[dict]:
    q, args = "SELECT * FROM checks WHERE monitor_id=?", [monitor_id]
    if since:
        q += " AND checked_at>=?"
        args.append(since)
    direction = "DESC" if newest_first else "ASC"
    q += f" ORDER BY checked_at {direction}, id {direction}"
    if limit:
        q += " LIMIT ?"
        args.append(limit)
    with connect() as c:
        return [_row(r) for r in c.execute(q, args).fetchall()]


def purge_old_checks(days: int) -> int:
    cutoff = iso(utcnow() - timedelta(days=days))
    with connect() as c:
        return c.execute("DELETE FROM checks WHERE checked_at<?", (cutoff,)).rowcount


# ---------- alerts ----------
def insert_alert(monitor_id: int, kind: str, message: str) -> dict:
    with connect() as c:
        cur = c.execute(
            "INSERT INTO alerts(monitor_id,kind,message,created_at) VALUES (?,?,?,?)",
            (monitor_id, kind, message, iso(utcnow())),
        )
        return _row(c.execute("SELECT * FROM alerts WHERE id=?", (cur.lastrowid,)).fetchone())


def list_alerts(limit: int = 50, monitor_id: Optional[int] = None) -> list[dict]:
    q = "SELECT a.*, m.name AS monitor_name FROM alerts a JOIN monitors m ON m.id=a.monitor_id"
    args: list = []
    if monitor_id:
        q += " WHERE a.monitor_id=?"
        args.append(monitor_id)
    q += " ORDER BY a.id DESC LIMIT ?"
    args.append(limit)
    with connect() as c:
        return [_row(r) for r in c.execute(q, args).fetchall()]
