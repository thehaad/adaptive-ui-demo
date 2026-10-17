"""Onboarding session records, persisted in SQLite (stdlib, no extra dependency).

Clients mint the session id and timestamps and sync their whole record with an
idempotent upsert, so retries and out-of-order requests are safe. Interaction
telemetry is a set of cumulative counters per event type (no event history).
"""

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MAX_LAYOUT_BYTES = 50_000
TELEMETRY_VERSION = 2

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
  id TEXT PRIMARY KEY,
  telemetry_version INTEGER NOT NULL,
  layout_source TEXT NOT NULL CHECK (layout_source IN ('static', 'ai', 'fallback')),
  preference TEXT,
  layout_id TEXT NOT NULL,
  layout_json TEXT NOT NULL,
  started_at TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('in_progress', 'completed')),
  selection_changed_count INTEGER NOT NULL DEFAULT 0 CHECK (selection_changed_count >= 0),
  navigation_next_count INTEGER NOT NULL DEFAULT 0 CHECK (navigation_next_count >= 0),
  navigation_back_count INTEGER NOT NULL DEFAULT 0 CHECK (navigation_back_count >= 0),
  interaction_count INTEGER NOT NULL DEFAULT 0,
  completed_at TEXT,
  CHECK (interaction_count = selection_changed_count + navigation_next_count + navigation_back_count)
)
"""

EVENT_TYPES = ("selection_changed", "navigation_next", "navigation_back")


class SessionConflict(Exception):
    pass


class EventCounts(BaseModel):
    """Cumulative counts per interaction event type. Unknown event types are rejected."""

    model_config = ConfigDict(extra="forbid")

    selection_changed: int = Field(ge=0, le=100_000)
    navigation_next: int = Field(ge=0, le=100_000)
    navigation_back: int = Field(ge=0, le=100_000)


class SessionRecord(BaseModel):
    layoutSource: Literal["static", "ai", "fallback"]
    preference: str | None = Field(default=None, min_length=1, max_length=500)
    layout: dict
    startedAt: datetime
    eventCounts: EventCounts
    interactionCount: int = Field(ge=0)
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
        if self.interactionCount != sum(self.eventCounts.model_dump().values()):
            raise ValueError("interactionCount must equal the sum of eventCounts")
        return self


def _canonical(value: dict) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def default_db_path() -> Path:
    return Path(__file__).parent / "data" / "sessions.db"


def db_path() -> Path:
    return Path(os.environ.get("ADAPTIVEUI_DB_PATH") or default_db_path())


def _connect() -> sqlite3.Connection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10, isolation_level=None)  # explicit transactions
    conn.row_factory = sqlite3.Row
    conn.execute(SCHEMA)
    return conn


def upsert_session(session_id: UUID, record: SessionRecord) -> dict:
    """Create the session, or merge a later snapshot of it. Safe to retry and to reorder."""
    sid = str(session_id)
    incoming = record.eventCounts.model_dump()
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
                "INSERT INTO sessions (id, telemetry_version, layout_source, preference, layout_id,"
                " layout_json, started_at, status, selection_changed_count, navigation_next_count,"
                " navigation_back_count, interaction_count, completed_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (sid, TELEMETRY_VERSION, *immutable.values(), "completed" if completed_at else "in_progress",
                 incoming["selection_changed"], incoming["navigation_next"], incoming["navigation_back"],
                 record.interactionCount, completed_at),
            )
        else:
            if any(row[key] != value for key, value in immutable.items()):
                raise SessionConflict("session already exists with different immutable fields")
            if row["completed_at"] is None:  # a completed session is frozen
                merged = {e: max(row[f"{e}_count"], incoming[e]) for e in EVENT_TYPES}
                completed_at = _iso(record.completedAt)
                conn.execute(
                    "UPDATE sessions SET selection_changed_count = ?, navigation_next_count = ?,"
                    " navigation_back_count = ?, interaction_count = ?, completed_at = ?, status = ?"
                    " WHERE id = ?",
                    (*(merged[e] for e in EVENT_TYPES), sum(merged.values()), completed_at,
                     "completed" if completed_at else "in_progress", sid),
                )
        result = conn.execute("SELECT * FROM sessions WHERE id = ?", (sid,)).fetchone()
        conn.execute("COMMIT")
        return {
            "status": result["status"],
            "interactionCount": result["interaction_count"],
            "eventCounts": {e: result[f"{e}_count"] for e in EVENT_TYPES},
            "completedAt": result["completed_at"],
        }
    except BaseException:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()
