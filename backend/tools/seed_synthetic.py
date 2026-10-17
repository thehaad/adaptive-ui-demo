"""Write clearly labeled SYNTHETIC onboarding history into an isolated database.

    uv run python -m tools.seed_synthetic --scenario guided_better --db /tmp/guided_better.db

Every row is marked: preference "[SYNTHETIC] ..." and layout id "ai-synthetic-...". The tool refuses
the default development database, and refuses any existing file that holds non-synthetic rows.
"""

import argparse
import os
import random
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid5, NAMESPACE_URL

from sessions import SessionRecord, default_db_path, upsert_session

SYNTHETIC_PREFERENCE = "[SYNTHETIC]"
SYNTHETIC_LAYOUT_PREFIX = "ai-synthetic-"

# Sessions per kind, per style. engaged/empty = completed with/without a selection; stalled = old,
# in progress, engaged; recent = in progress, younger than the stall window; idle = old, no interaction.
SCENARIOS = {
    "guided_better": {
        "guided": dict(engaged=30, empty=0, stalled=6, recent=3, idle=2),
        "compact": dict(engaged=10, empty=4, stalled=20, recent=2, idle=3),
    },
    "compact_better": {
        "guided": dict(engaged=10, empty=1, stalled=20, recent=3, idle=2),
        "compact": dict(engaged=30, empty=4, stalled=6, recent=2, idle=3),
    },
    "balanced": {
        "guided": dict(engaged=20, empty=1, stalled=10, recent=2, idle=2),
        "compact": dict(engaged=19, empty=3, stalled=11, recent=2, idle=2),
    },
    "no_history": {  # too little mature evidence in either group to be usable
        "guided": dict(engaged=3, empty=1, stalled=2, recent=4, idle=2),
        "compact": dict(engaged=2, empty=1, stalled=1, recent=4, idle=2),
    },
}

_SELECTOR = lambda label, option_set: {"component": "PreferenceSelector", "props": {"label": label, "optionSet": option_set}}
_FINISH = {"component": "ActionButton", "props": {"label": "Finish", "action": "complete_onboarding"}}
_CARD = {"component": "WelcomeCard", "props": {"title": "Synthetic welcome", "message": "Synthetic test copy."}}

LAYOUTS = {
    "guided": [
        ("a", [_CARD, _SELECTOR("Where?", "workout_location"), _SELECTOR("How long?", "session_length"), _FINISH]),
        ("b", [_CARD, _SELECTOR("Level?", "experience_level"), _SELECTOR("Focus?", "workout_focus"), _SELECTOR("Length?", "session_length"), _FINISH]),
        ("c", [_SELECTOR("Where?", "workout_location"), _SELECTOR("Focus?", "workout_focus"), _FINISH]),
    ],
    "compact": [
        ("a", [_SELECTOR("Level", "experience_level"), _SELECTOR("Focus", "workout_focus"), _FINISH]),
        ("b", [_SELECTOR("Level", "experience_level"), _SELECTOR("Focus", "workout_focus"), _SELECTOR("Length", "session_length"), _FINISH]),
        ("c", [_SELECTOR("Where", "workout_location"), _SELECTOR("Length", "session_length"), _SELECTOR("Level", "experience_level"), _FINISH]),
    ],
}


def layout_for(style: str, index: int) -> dict:
    variant, children = LAYOUTS[style][index % 3]
    props = {"density": "comfortable"} if style == "guided" else {"direction": "row", "breakpoint": 700, "density": "compact"}
    return {
        "id": f"{SYNTHETIC_LAYOUT_PREFIX}{style}-{variant}",
        "root": {"component": "Steps" if style == "guided" else "Row", "props": props, "children": children},
    }


def _counts(rng: random.Random, style: str, kind: str) -> tuple[int, int, int]:
    """(selections, next, back) for one synthetic session."""
    guided = style == "guided"
    if kind == "engaged":
        return rng.randint(2, 4), rng.randint(3, 6) if guided else 0, rng.randint(0, 3) if guided else 0
    if kind == "empty":
        return 0, rng.randint(3, 5) if guided else 0, 0
    if kind == "stalled":
        sel = rng.randint(0, 2) if guided else rng.randint(1, 2)
        nxt = rng.randint(1, 3) if guided else 0
        return sel, nxt, rng.randint(0, 1) if guided else 0
    if kind == "recent":
        return (rng.randint(0, 1), rng.randint(1, 2), 0) if guided else (rng.randint(1, 3), 0, 0)
    return 0, 0, 0  # idle


def build_sessions(scenario: str, now: datetime) -> list[tuple[str, SessionRecord]]:
    sessions = []
    for style, kinds in SCENARIOS[scenario].items():
        for kind, count in kinds.items():
            for i in range(count):
                tag = f"{scenario}/{style}/{kind}/{i}"
                rng = random.Random(tag)  # deterministic: same scenario and `now`, same rows
                sel, nxt, back = _counts(rng, style, kind)
                age = timedelta(minutes=rng.randint(1, 30) if kind == "recent" else rng.randint(120, 12_000))
                started = (now - age).replace(microsecond=0)
                completed = started + timedelta(minutes=rng.randint(2, 15)) if kind in ("engaged", "empty") else None
                sessions.append((str(uuid5(NAMESPACE_URL, tag)), SessionRecord(
                    layoutSource="ai",
                    preference=f"{SYNTHETIC_PREFERENCE} {tag}",
                    layout=layout_for(style, i),
                    startedAt=started,
                    eventCounts=dict(selection_changed=sel, navigation_next=nxt, navigation_back=back),
                    interactionCount=sel + nxt + back,
                    completedAt=completed,
                )))
    return sessions


def refuse_reason(target: Path) -> str | None:
    """Why this target must not be written, or None. Looks at the path first and opens nothing."""
    if target.resolve() == default_db_path().resolve():
        return "refusing the default development database"
    if target.exists():
        conn = sqlite3.connect(f"{target.resolve().as_uri()}?mode=ro", uri=True)
        try:
            real = conn.execute(
                "SELECT COUNT(*) FROM sessions WHERE NOT (layout_source = 'ai'"
                " AND COALESCE(preference, '') LIKE ? AND layout_id LIKE ?)",  # COALESCE: NULL must count as real
                (f"{SYNTHETIC_PREFERENCE}%", f"{SYNTHETIC_LAYOUT_PREFIX}%"),
            ).fetchone()[0]
        except sqlite3.OperationalError:
            real = 0  # no sessions table
        finally:
            conn.close()
        if real:
            return f"refusing {target}: it already holds {real} non-synthetic session(s)"
    return None


def seed(scenario: str, target: Path, now: datetime) -> int:
    reason = refuse_reason(target)
    if reason:
        raise SystemExit(reason)
    previous = os.environ.get("ADAPTIVEUI_DB_PATH")
    os.environ["ADAPTIVEUI_DB_PATH"] = str(target)  # the production writer, pointed at the isolated file
    try:
        sessions = build_sessions(scenario, now)
        for session_id, record in sessions:
            upsert_session(session_id, record)
        return len(sessions)
    finally:
        if previous is None:
            os.environ.pop("ADAPTIVEUI_DB_PATH", None)
        else:
            os.environ["ADAPTIVEUI_DB_PATH"] = previous


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write SYNTHETIC onboarding history to an isolated database.")
    parser.add_argument("--scenario", required=True, choices=sorted(SCENARIOS))
    parser.add_argument("--db", required=True, help="target database file (never the default development database)")
    parser.add_argument("--now", help="ISO timestamp the history is relative to (default: current time)")
    args = parser.parse_args(argv)
    now = datetime.fromisoformat(args.now.replace("Z", "+00:00")) if args.now else datetime.now(timezone.utc)
    n = seed(args.scenario, Path(args.db), now)
    print(f"Wrote {n} SYNTHETIC sessions ({args.scenario}) to {args.db}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
