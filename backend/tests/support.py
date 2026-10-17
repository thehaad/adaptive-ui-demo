"""Shared helpers: temporary databases and hand-built sessions. Everything here is offline."""

import os
import tempfile
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock
from uuid import uuid4

from sessions import SessionRecord, upsert_session
from tools.seed_synthetic import layout_for

NOW = datetime(2026, 10, 17, 12, 0, tzinfo=timezone.utc)


def temp_db_path() -> Path:
    directory = tempfile.mkdtemp(prefix="adaptiveui-test-")
    return Path(directory) / "sessions.db"


@contextmanager
def configured_db(path: Path):
    """Point the production writer/reader at an isolated file."""
    with mock.patch.dict(os.environ, {"ADAPTIVEUI_DB_PATH": str(path)}):
        yield


def put_session(
    path: Path,
    *,
    style: str = "guided",
    source: str = "ai",
    age: timedelta = timedelta(hours=5),
    selections: int = 0,
    nxt: int = 0,
    back: int = 0,
    completed: bool = False,
    preference: str | None = "[SYNTHETIC] test",
    layout: dict | None = None,
) -> str:
    started = NOW - age
    session_id = str(uuid4())
    record = SessionRecord(
        layoutSource=source,
        preference=preference if source == "ai" else None,
        layout=layout or layout_for(style, 0),
        startedAt=started,
        eventCounts=dict(selection_changed=selections, navigation_next=nxt, navigation_back=back),
        interactionCount=selections + nxt + back,
        completedAt=started + timedelta(minutes=5) if completed else None,
    )
    with configured_db(path):
        upsert_session(session_id, record)
    return session_id
