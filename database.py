import sqlite3
import hashlib
import os
from datetime import datetime
from pathlib import Path
from config import DB_PATH


def _connect():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")  # allow concurrent reads
    return conn


def init_db():
    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS events (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp        TEXT NOT NULL,
                event_type       TEXT NOT NULL,
                severity         TEXT NOT NULL,
                title            TEXT NOT NULL,
                details          TEXT,
                screenshot_path  TEXT,
                event_key        TEXT UNIQUE,
                acknowledged     INTEGER DEFAULT 0
            );

            CREATE INDEX IF NOT EXISTS idx_timestamp  ON events(timestamp);
            CREATE INDEX IF NOT EXISTS idx_event_type ON events(event_type);
            CREATE INDEX IF NOT EXISTS idx_event_key  ON events(event_key);

            CREATE TABLE IF NOT EXISTS credentials (
                id            INTEGER PRIMARY KEY,
                username      TEXT NOT NULL,
                password_hash TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS monitor_sessions (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                start_time TEXT NOT NULL,
                end_time   TEXT,
                hostname   TEXT,
                os_user    TEXT
            );

            CREATE TABLE IF NOT EXISTS screenshot_requests (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id     INTEGER NOT NULL,
                requested_at TEXT NOT NULL,
                fulfilled    INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT
            );
        """)


# ── Settings (key/value, shared between service and dashboard) ────────────────

def get_setting(key: str, default: str | None = None) -> str | None:
    try:
        with _connect() as conn:
            row = conn.execute(
                "SELECT value FROM settings WHERE key=?", (key,)
            ).fetchone()
        return row[0] if row else default
    except Exception:
        return default


def set_setting(key: str, value: str):
    with _connect() as conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value)
        )


def log_event(event_type, severity, title, details=None,
              screenshot_path=None, event_key=None):
    """Insert an event; silently ignore duplicate event_keys.
    Returns the new event's id, or None if it was a duplicate (or on error) -
    callers use this to know whether to request a screenshot for it."""
    ts = datetime.now().isoformat(sep=' ', timespec='seconds')
    try:
        with _connect() as conn:
            cur = conn.execute(
                """INSERT OR IGNORE INTO events
                   (timestamp, event_type, severity, title, details,
                    screenshot_path, event_key)
                   VALUES (?,?,?,?,?,?,?)""",
                (ts, event_type, severity, title, details,
                 screenshot_path, event_key)
            )
            return cur.lastrowid if cur.rowcount else None
    except Exception:
        return None


def event_key_exists(event_key):
    with _connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM events WHERE event_key=?", (event_key,)
        ).fetchone()
    return row is not None


def get_events(event_type=None, limit=2000):
    query = """
        SELECT id, timestamp, event_type, severity, title,
               details, screenshot_path, acknowledged
        FROM events
    """
    params = []
    if event_type and event_type != "all":
        query += " WHERE event_type = ?"
        params.append(event_type)
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    with _connect() as conn:
        return conn.execute(query, params).fetchall()


def get_stats():
    with _connect() as conn:
        return conn.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN severity='critical' THEN 1 ELSE 0 END) as critical,
                SUM(CASE WHEN severity='warning'  THEN 1 ELSE 0 END) as warning,
                SUM(acknowledged=0)                                    as unread
            FROM events
        """).fetchone()


def acknowledge_event(event_id):
    with _connect() as conn:
        conn.execute("UPDATE events SET acknowledged=1 WHERE id=?", (event_id,))


def acknowledge_all():
    with _connect() as conn:
        conn.execute("UPDATE events SET acknowledged=1")


def delete_event(event_id):
    with _connect() as conn:
        conn.execute("DELETE FROM events WHERE id=?", (event_id,))


# ── Screenshot requests ──────────────────────────────────────────────────────
# The monitor service runs as LocalSystem in Session 0, which has no desktop
# and so cannot grab a screenshot itself (Windows session isolation). It
# leaves a request here instead; session_agent.py, running in the actual
# competitor's own logon session, polls for these and fulfills them.

def request_screenshot(event_id):
    with _connect() as conn:
        conn.execute(
            "INSERT INTO screenshot_requests (event_id, requested_at) VALUES (?,?)",
            (event_id, datetime.now().isoformat(sep=' ', timespec='seconds'))
        )


def get_pending_screenshot_requests(limit=20):
    with _connect() as conn:
        return conn.execute(
            """SELECT id, event_id, requested_at FROM screenshot_requests
               WHERE fulfilled=0 ORDER BY id LIMIT ?""",
            (limit,)
        ).fetchall()


def fulfill_screenshot_request(request_id, event_id, screenshot_path):
    with _connect() as conn:
        conn.execute("UPDATE screenshot_requests SET fulfilled=1 WHERE id=?", (request_id,))
        if screenshot_path:
            conn.execute("UPDATE events SET screenshot_path=? WHERE id=?", (screenshot_path, event_id))


# ── Credentials ─────────────────────────────────────────────────────────────

def _hash(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def has_credentials() -> bool:
    with _connect() as conn:
        return conn.execute("SELECT COUNT(*) FROM credentials").fetchone()[0] > 0


def set_credentials(username: str, password: str):
    with _connect() as conn:
        conn.execute("DELETE FROM credentials")
        conn.execute(
            "INSERT INTO credentials (username, password_hash) VALUES (?,?)",
            (username, _hash(password))
        )


def verify_credentials(username: str, password: str) -> bool:
    with _connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM credentials WHERE username=? AND password_hash=?",
            (username, _hash(password))
        ).fetchone()
    return row is not None


# ── Session logging ──────────────────────────────────────────────────────────

def start_session() -> int:
    import socket
    hostname = socket.gethostname()
    os_user  = os.environ.get("USERNAME", "unknown")
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO monitor_sessions (start_time, hostname, os_user) VALUES (?,?,?)",
            (datetime.now().isoformat(sep=' ', timespec='seconds'), hostname, os_user)
        )
        return cur.lastrowid


def end_session(session_id: int):
    with _connect() as conn:
        conn.execute(
            "UPDATE monitor_sessions SET end_time=? WHERE id=?",
            (datetime.now().isoformat(sep=' ', timespec='seconds'), session_id)
        )
