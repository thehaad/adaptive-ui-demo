"""Onboarding session records, persisted in SQLite (stdlib, no extra dependency).

Clients mint the session id and timestamps and sync their whole record with an
idempotent upsert, so retries and out-of-order requests are safe.
"""

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

MAX_LAYOUT_BYTES = 50_000

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
  id TEXT PRIMARY KEY,
  layout_source TEXT NOT NULL CHECK (layout_source IN ('static', 'ai', 'fallback')),
  preference TEXT,
  layout_id TEXT NOT NULL,
  layout_json TEXT NOT NULL,
  started_at TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('in_progress', 'completed')),
  interaction_count INTEGER NOT NULL DEFAULT 0,
  completed_at TEXT
)
"""


class SessionConflict(Exception):
    pass


class SessionRecord(BaseModel):
    layoutSource: Literal["static", "ai", "fallback"]
    preference: str | None = Field(default=None, min_length=1, max_length=500)
    layout: dict
    startedAt: datetime
    interactionCount: int = Field(ge=0, le=100_000)
    completedAt: datetime | None = None

    @field_validator("startedAt", "completedAt")
    @classmethod
    def _require_timezone(cls, value: datetime | None):
        if value is not None and value.tzinfo is None:
            raise ValueError("timestamp must include a timezone")
        return value

    @model_validator(mode="after")
    def _check(self):
        if not isinstance(self.layout.get("id"), str) or not isinstance(self.layout.get("root"), dict):
            raise ValueError("layout must have a string id and an object root")
        if len(_canonical(self.layout)) > MAX_LAYOUT_BYTES:
            raise ValueError("layout is too large")
        if (self.layoutSource == "ai") != (self.preference is not None):
            raise ValueError("preference is required for, and only allowed on, ai sessions")
        if self.completedAt is not None and self.completedAt < self.startedAt:
            raise ValueError("completedAt is before startedAt")
        return self


def _canonical(value: dict) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _connect() -> sqlite3.Connection:
    path = Path(os.environ.get("ADAPTIVEUI_DB_PATH") or Path(__file__).parent / "data" / "sessions.db")
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10, isolation_level=None)  # explicit transactions
    conn.row_factory = sqlite3.Row
    conn.execute(SCHEMA)
    return conn


def upsert_session(session_id: UUID, record: SessionRecord) -> dict:
    """Create the session, or merge a later snapshot of it. Safe to retry and to reorder."""
    sid = str(session_id)
    immutable = {
        "layout_source": record.layoutSource,
        "preference": record.preference,
        "layout_id": record.layout["id"],
        "layout_json": _canonical(record.layout),
        "started_at": _iso(record.startedAt),
    }
    conn = _connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT * FROM sessions WHERE id = ?", (sid,)).fetchone()
        if row is None:
            completed_at = _iso(record.completedAt)
            conn.execute(
                "INSERT INTO sessions (id, layout_source, preference, layout_id, layout_json, started_at,"
                " status, interaction_count, completed_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (sid, *immutable.values(), "completed" if completed_at else "in_progress",
                 record.interactionCount, completed_at),
            )
        else:
            if any(row[key] != value for key, value in immutable.items()):
                raise SessionConflict("session already exists with different immutable fields")
            if row["completed_at"] is None:  # a completed session is frozen
                completed_at = _iso(record.completedAt)
                conn.execute(
                    "UPDATE sessions SET interaction_count = MAX(interaction_count, ?),"
                    " completed_at = ?, status = ? WHERE id = ?",
                    (record.interactionCount, completed_at, "completed" if completed_at else "in_progress", sid),
                )
        result = conn.execute(
            "SELECT status, interaction_count, completed_at FROM sessions WHERE id = ?", (sid,)
        ).fetchone()
        conn.execute("COMMIT")
        return {
            "status": result["status"],
            "interactionCount": result["interaction_count"],
            "completedAt": result["completed_at"],
        }
    except BaseException:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()
