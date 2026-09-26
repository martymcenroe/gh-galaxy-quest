"""n3_triage_queue — Persist scored discussions to SQLite state database."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from .n2_relevance_score import ScoredDiscussion


DEFAULT_DB_PATH = Path(__file__).parent.parent.parent / "data" / "state.db"


def _get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or DEFAULT_DB_PATH
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS discussions (
            id TEXT PRIMARY KEY,
            number INTEGER NOT NULL,
            repo TEXT NOT NULL,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            score REAL NOT NULL,
            matched_domains TEXT NOT NULL,
            matched_keywords TEXT NOT NULL,
            created_at TEXT NOT NULL,
            first_seen_at TEXT NOT NULL DEFAULT (datetime('now')),
            status TEXT NOT NULL DEFAULT 'new'
        )
    """)
    conn.commit()
    return conn


def upsert_discussions(
    scored: list[ScoredDiscussion],
    db_path: Path | None = None,
) -> int:
    """Insert or update scored discussions. Returns count of new insertions."""
    conn = _get_connection(db_path)
    new_count = 0

    for s in scored:
        cursor = conn.execute("SELECT id FROM discussions WHERE id = ?", (s.discussion.id,))
        if cursor.fetchone() is None:
            conn.execute(
                """INSERT INTO discussions
                   (id, number, repo, title, url, score, matched_domains, matched_keywords, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    s.discussion.id,
                    s.discussion.number,
                    s.discussion.repo_full_name,
                    s.discussion.title,
                    s.discussion.url,
                    s.score,
                    ",".join(s.matched_domains),
                    ",".join(s.matched_keywords),
                    s.discussion.created_at,
                ),
            )
            new_count += 1
        else:
            conn.execute(
                "UPDATE discussions SET score = ?, matched_domains = ?, matched_keywords = ? WHERE id = ?",
                (
                    s.score,
                    ",".join(s.matched_domains),
                    ",".join(s.matched_keywords),
                    s.discussion.id,
                ),
            )

    conn.commit()
    conn.close()
    return new_count


def get_actionable(
    db_path: Path | None = None,
    limit: int = 20,
) -> list[dict]:
    """Get top-scored discussions that haven't been answered or ignored."""
    conn = _get_connection(db_path)
    rows = conn.execute(
        """SELECT id, number, repo, title, url, score, matched_domains, matched_keywords, created_at
           FROM discussions
           WHERE status = 'new'
           ORDER BY score DESC
           LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()

    return [
        {
            "id": r[0],
            "number": r[1],
            "repo": r[2],
            "title": r[3],
            "url": r[4],
            "score": r[5],
            "matched_domains": r[6].split(","),
            "matched_keywords": r[7].split(","),
            "created_at": r[8],
        }
        for r in rows
    ]


def mark_status(
    discussion_id: str,
    status: str,
    db_path: Path | None = None,
) -> None:
    """Mark a discussion as answered, ignored, or new."""
    conn = _get_connection(db_path)
    conn.execute(
        "UPDATE discussions SET status = ? WHERE id = ?",
        (status, discussion_id),
    )
    conn.commit()
    conn.close()
