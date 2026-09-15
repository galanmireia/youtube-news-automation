import sqlite3
import time
from contextlib import contextmanager

from .config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS processed_sources (
    source_url TEXT PRIMARY KEY,
    processed_at REAL NOT NULL,
    title TEXT
);

CREATE TABLE IF NOT EXISTS videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at REAL NOT NULL,
    source_url TEXT,
    variant TEXT NOT NULL DEFAULT 'long',
    title TEXT,
    description TEXT,
    tags TEXT,
    video_path TEXT,
    thumbnail_path TEXT,
    subtitle_path TEXT,
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
        # Migrations for columns added after the table already existed on disk.
        for migration in (
            "ALTER TABLE videos ADD COLUMN variant TEXT NOT NULL DEFAULT 'long'",
            "ALTER TABLE videos ADD COLUMN subtitle_path TEXT",
            "ALTER TABLE processed_sources ADD COLUMN title TEXT",
        ):
            try:
                conn.execute(migration)
            except sqlite3.OperationalError as exc:
                if "duplicate column name" not in str(exc):
                    raise

        # Backfill headlines for stories processed before the column existed,
        # otherwise they stay invisible to the duplicate check and can be
        # made a second time. The videos table keeps the rewritten SEO title
        # rather than the original headline, but it describes the same story
        # closely enough for a vocabulary comparison.
        conn.execute(
            "UPDATE processed_sources SET title = ("
            "  SELECT v.title FROM videos v"
            "  WHERE v.source_url = processed_sources.source_url AND v.title IS NOT NULL"
            "  LIMIT 1"
            ") WHERE title IS NULL OR title = ''"
        )


def is_source_processed(source_url: str) -> bool:
    with get_conn() as conn:
        row = conn.execute("SELECT 1 FROM processed_sources WHERE source_url = ?", (source_url,)).fetchone()
    return row is not None


def mark_source_processed(source_url: str, title: str = "") -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO processed_sources (source_url, processed_at, title) VALUES (?, ?, ?)",
            (source_url, time.time(), title),
        )


def recent_processed_titles(limit: int = 80) -> list[str]:
    """Headlines of the stories already covered, most recent first.

    Marking a story as done by URL alone isn't enough: the same story
    reaches us through every feed with a different link, so it came back
    around and got made twice."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT title FROM processed_sources WHERE title IS NOT NULL AND title != ''"
            " ORDER BY processed_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [row["title"] for row in rows]


def all_referenced_paths() -> set[str]:
    """Every on-disk file any video record still points at. Anything else
    under the data directory is left over from a build and can go."""
    with get_conn() as conn:
        rows = conn.execute("SELECT video_path, thumbnail_path, subtitle_path FROM videos").fetchall()
    return {value for row in rows for value in (row["video_path"], row["thumbnail_path"], row["subtitle_path"]) if value}


def clear_processed_sources() -> int:
    """Forgets every 'already processed' RSS entry, so the next run can pick
    any current feed item again (including ones already turned into a video
    before). Returns how many entries were cleared."""
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM processed_sources")
        return cur.rowcount


def create_video_record(
    *,
    source_url: str,
    variant: str,
    title: str,
    description: str,
    tags: list[str],
    video_path: str,
    thumbnail_path: str,
    subtitle_path: str,
) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO videos (created_at, source_url, variant, title, description, tags, video_path, thumbnail_path, subtitle_path, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')""",
            (
                time.time(),
                source_url,
                variant,
                title,
                description,
                ",".join(tags),
                video_path,
                thumbnail_path,
                subtitle_path,
            ),
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


# Videos in these statuses are done for good (either live on YouTube or
# discarded) - nothing ever needs their on-disk clips/audio/final video again.
_FINISHED_STATUSES = ("uploaded", "rejected")


def list_finished_videos() -> list[sqlite3.Row]:
    with get_conn() as conn:
        placeholders = ",".join("?" for _ in _FINISHED_STATUSES)
        return conn.execute(
            f"SELECT * FROM videos WHERE status IN ({placeholders})", _FINISHED_STATUSES
        ).fetchall()
