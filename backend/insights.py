"""Deterministic aggregate outcomes from stored onboarding sessions.

Groups AI-composed sessions by layout structure (guided vs compact) and summarizes how they
ended. The result is observational: Claude picks a layout from each user's stated preference,
so the groups contain different people and differences are not causal. Only aggregates leave
this module: never session ids, timestamps, preferences or layouts.

Read-only: the database is opened with mode=ro and is never created or written.
"""

import argparse
import json
import logging
import math
import os
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sessions import db_path

# Provisional thresholds (named constants, not tuned).
STALL_AFTER = timedelta(minutes=60)  # in-progress sessions younger than this are not judged
MIN_INTERACTIONS = 1  # a stalled session must show some engagement
MIN_MATURE = 10  # mature sessions a group needs before a ratio or comparison is reported
WILSON_Z = 1.96  # 95% interval

STYLES = {"guided": "Steps root", "compact": "Row root, compact density"}
TELEMETRY_VERSION = 2

log = logging.getLogger("insights")


def classify_style(layout_json: str) -> str | None:
    """guided = Steps root; compact = Row root with compact density; anything else is excluded."""
    try:
        root = json.loads(layout_json)["root"]
        component = root["component"]
        props = root.get("props")
    except (ValueError, KeyError, TypeError, AttributeError):
        return None
    if component == "Steps":
        return "guided"
    if component == "Row" and isinstance(props, dict) and props.get("density") == "compact":
        return "compact"
    return None


def classify_outcome(row: sqlite3.Row, now: datetime) -> str:
    """engaged_completion | empty_completion | stalled | insufficient.

    A completed session with no selection is an empty completion: never a failure, and not
    counted as success. An in-progress session is only "potentially stalled" once it is mature
    and shows engagement; everything else carries no evidence either way.
    """
    if row["status"] == "completed":
        return "engaged_completion" if row["selection_changed_count"] >= 1 else "empty_completion"
    started = datetime.fromisoformat(row["started_at"].replace("Z", "+00:00"))
    if now - started >= STALL_AFTER and row["interaction_count"] >= MIN_INTERACTIONS:
        return "stalled"
    return "insufficient"


def wilson_interval(successes: int, n: int, z: float = WILSON_Z) -> tuple[float, float]:
    p = successes / n
    denominator = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denominator
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return max(0.0, center - half), min(1.0, center + half)


def _empty_group() -> dict:
    return {"sessions": 0, "technical_completions": 0, "engaged_completions": 0, "empty_completions": 0,
            "stalled": 0, "insufficient": 0, "_engaged": []}


def compute_insights(path: Path | str | None = None, now: datetime | None = None) -> dict:
    """Aggregate outcomes per structural group. `now` is injectable for deterministic tests."""
    now = now or datetime.now(timezone.utc)
    path = Path(path) if path else db_path()
    groups = {name: _empty_group() for name in STYLES}
    other_layouts = 0

    rows: list[sqlite3.Row] = []
    if path.exists():  # never create the file: open read-only
        conn = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                "SELECT layout_json, status, started_at, interaction_count, selection_changed_count,"
                " navigation_next_count, navigation_back_count FROM sessions"
                " WHERE layout_source = 'ai' AND telemetry_version = ?",
                (TELEMETRY_VERSION,),
            ).fetchall()
        except sqlite3.OperationalError:  # no sessions table yet
            rows = []
        finally:
            conn.close()

    for row in rows:
        style = classify_style(row["layout_json"])
        if style is None:
            other_layouts += 1
            continue
        group = groups[style]
        outcome = classify_outcome(row, now)
        group["sessions"] += 1
        if outcome == "engaged_completion":
            group["technical_completions"] += 1
            group["engaged_completions"] += 1
            group["_engaged"].append(row)
        elif outcome == "empty_completion":
            group["technical_completions"] += 1
            group["empty_completions"] += 1
        elif outcome == "stalled":
            group["stalled"] += 1
        else:
            group["insufficient"] += 1

    for group in groups.values():
        engaged = group.pop("_engaged")
        group["mature"] = group["engaged_completions"] + group["stalled"]
        group["reportable"] = group["mature"] >= MIN_MATURE
        group["ratio"] = group["interval"] = None
        group["means"] = None
        if group["reportable"]:
            group["ratio"] = group["engaged_completions"] / group["mature"]
            group["interval"] = wilson_interval(group["engaged_completions"], group["mature"])
        if engaged:
            mean = lambda column: sum(r[column] for r in engaged) / len(engaged)
            group["means"] = {
                "interactions": mean("interaction_count"),
                "selections": mean("selection_changed_count"),
                "next": mean("navigation_next_count"),
                "back": mean("navigation_back_count"),
                "backtrack_share": sum(1 for r in engaged if r["navigation_back_count"] >= 1) / len(engaged),
            }

    comparison = {"state": "not_possible", "leader": None}
    guided, compact = groups["guided"], groups["compact"]
    if guided["reportable"] and compact["reportable"]:
        disjoint = guided["interval"][0] > compact["interval"][1] or compact["interval"][0] > guided["interval"][1]
        if disjoint:
            comparison = {"state": "clear", "leader": "guided" if guided["ratio"] > compact["ratio"] else "compact"}
        else:
            comparison = {"state": "none", "leader": None}

    return {
        "groups": groups,
        "other_layouts": other_layouts,
        "excluded_insufficient": sum(g["insufficient"] + g["empty_completions"] for g in groups.values()),
        "comparison": comparison,
        "usable": any(g["reportable"] for g in groups.values()),
    }


def _pct(x: float) -> str:
    return f"{x * 100:.0f}%"


def render_insights(insights: dict) -> str:
    """A short, deterministic summary. Contains only aggregate numbers and fixed wording."""
    lines = [
        "Aggregate outcomes from past AI-composed onboarding sessions. Observational only: "
        "each layout was chosen from that user's stated preference, so the groups contain "
        "different people and differences are not causal."
    ]
    for name, description in STYLES.items():
        g = insights["groups"][name]
        head = f"- {name} ({description}): "
        if not g["reportable"]:
            lines.append(head + f"{g['mature']} mature sessions, too few to report a ratio (minimum {MIN_MATURE}).")
            continue
        low, high = g["interval"]
        text = (
            f"{g['mature']} mature sessions: {g['engaged_completions']} engaged completions (completed with "
            f"at least one selection), {g['stalled']} potentially stalled (in progress, not completed in "
            f"telemetry; not confirmed as abandoned). Provisional completion ratio {_pct(g['ratio'])} "
            f"(95% interval {_pct(low)}-{_pct(high)})."
        )
        m = g["means"]
        if m is None:  # mature sessions exist but none is an engaged completion
            text += " No engaged completions yet."
        else:
            text += f" Engaged completions average {m['interactions']:.1f} interactions"
            if name == "guided":
                text += f", {m['back']:.1f} back-steps; {_pct(m['backtrack_share'])} went back at least once"
            text += "."
        lines.append(head + text)
    cmp_ = insights["comparison"]
    if cmp_["state"] == "clear":
        lines.append(f"Comparison: provisional ratio is clearly higher for {cmp_['leader']} (intervals do not overlap); still observational.")
    elif cmp_["state"] == "none":
        lines.append("Comparison: no clear difference (intervals overlap).")
    else:
        lines.append("Comparison: not possible (a group has too few mature sessions).")
    lines.append(f"{insights['excluded_insufficient']} sessions excluded as insufficient data (too recent, no interaction, or empty completion).")
    return "\n".join(lines)


def insights_for_prompt(path: Path | str | None = None, now: datetime | None = None) -> str | None:
    """Text to give Claude, or None. Fails open: any problem means ordinary composition."""
    if os.environ.get("ADAPTIVEUI_INSIGHTS", "").lower() == "off":
        return None
    try:
        computed = compute_insights(path, now)
        return render_insights(computed) if computed["usable"] else None
    except Exception as error:  # never let analytics break onboarding
        log.warning("insights unavailable (%s)", type(error).__name__)
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Print onboarding outcome insights (read-only).")
    parser.add_argument("--db", help="database file (default: the configured sessions database)")
    parser.add_argument("--now", help="ISO timestamp to evaluate against (default: current time)")
    parser.add_argument("--json", action="store_true", help="print the computed aggregates as JSON")
    args = parser.parse_args(argv)
    now = datetime.fromisoformat(args.now.replace("Z", "+00:00")) if args.now else None
    computed = compute_insights(args.db, now)
    if args.json:
        print(json.dumps(computed, indent=2, sort_keys=True))
        return 0
    print(render_insights(computed))
    print()
    if computed["usable"]:
        print("Supplied to Claude: yes (the summary above, inside the historical-evidence block).")
    else:
        print("Supplied to Claude: no (no group has enough mature sessions; composition is unchanged).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
