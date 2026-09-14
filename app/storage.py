import sqlite3
import time
from contextlib import contextmanager

from .config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS processed_sources (
    source_url TEXT PRIMARY KEY,
    processed_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at REAL NOT NULL,
    source_url TEXT,
    title TEXT,
    description TEXT,
    tags TEXT,
    video_path TEXT,
    thumbnail_path TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    telegram_chat_id TEXT,
    telegram_message_id TEXT,
    youtube_video_id TEXT
);
"""


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(SCHEMA)


def is_source_processed(source_url: str) -> bool:
    with get_conn() as conn:
        row = conn.execute("SELECT 1 FROM processed_sources WHERE source_url = ?", (source_url,)).fetchone()
    return row is not None


def mark_source_processed(source_url: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO processed_sources (source_url, processed_at) VALUES (?, ?)",
            (source_url, time.time()),
        )


def create_video_record(*, source_url: str, title: str, description: str, tags: list[str], video_path: str, thumbnail_path: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO videos (created_at, source_url, title, description, tags, video_path, thumbnail_path, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')""",
            (time.time(), source_url, title, description, ",".join(tags), video_path, thumbnail_path),
        )
        return cur.lastrowid


def set_telegram_message(video_id: int, chat_id: str, message_id: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE videos SET telegram_chat_id = ?, telegram_message_id = ? WHERE id = ?",
            (chat_id, message_id, video_id),
        )


def get_video(video_id: int) -> sqlite3.Row | None:
    with get_conn() as conn:
        return conn.execute("SELECT * FROM videos WHERE id = ?", (video_id,)).fetchone()


def set_status(video_id: int, status: str, youtube_video_id: str | None = None) -> None:
    with get_conn() as conn:
        if youtube_video_id is not None:
            conn.execute(
                "UPDATE videos SET status = ?, youtube_video_id = ? WHERE id = ?",
                (status, youtube_video_id, video_id),
            )
        else:
            conn.execute("UPDATE videos SET status = ? WHERE id = ?", (status, video_id))
