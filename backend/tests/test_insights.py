import hashlib
import unittest
from datetime import timedelta

import insights
from insights import compute_insights, render_insights, wilson_interval
from tests.support import NOW, put_session, temp_db_path
from tools.seed_synthetic import seed


def group(db, name):
    return compute_insights(db, NOW)["groups"][name]


class ClassificationTests(unittest.TestCase):
    def setUp(self):
        self.db = temp_db_path()

    def test_engaged_completion_needs_a_selection(self):
        put_session(self.db, completed=True, selections=2, nxt=3)
        put_session(self.db, completed=True, selections=0, nxt=3)  # empty completion
        g = group(self.db, "guided")
        self.assertEqual((g["technical_completions"], g["engaged_completions"], g["empty_completions"]), (2, 1, 1))

    def test_empty_completion_is_neither_success_nor_failure(self):
        put_session(self.db, completed=True, selections=0, nxt=3)
        g = group(self.db, "guided")
        self.assertEqual((g["mature"], g["stalled"], g["engaged_completions"]), (0, 0, 0))
        self.assertEqual(compute_insights(self.db, NOW)["excluded_insufficient"], 1)

    def test_stalled_needs_age_and_engagement(self):
        put_session(self.db, age=timedelta(hours=2), selections=1)                 # stalled
        put_session(self.db, age=timedelta(minutes=59), selections=1)              # too recent
        put_session(self.db, age=timedelta(minutes=60), selections=1)              # exactly mature
        put_session(self.db, age=timedelta(hours=9))                               # old but no interaction
        g = group(self.db, "guided")
        self.assertEqual(g["stalled"], 2)
        self.assertEqual(g["insufficient"], 2)

    def test_in_progress_is_not_counted_as_abandonment_by_default(self):
        for _ in range(5):
            put_session(self.db, age=timedelta(minutes=10), selections=1)
        g = group(self.db, "guided")
        self.assertEqual((g["stalled"], g["mature"], g["insufficient"]), (0, 0, 5))

    def test_only_ai_sessions_and_known_structures_are_grouped(self):
        put_session(self.db, source="static", preference=None, completed=True, selections=1)
        put_session(self.db, source="fallback", preference=None, completed=True, selections=1)
        comfortable_row = {"id": "ai-x", "root": {"component": "Row", "props": {"density": "comfortable"}, "children": []}}
        put_session(self.db, completed=True, selections=1, layout=comfortable_row)
        result = compute_insights(self.db, NOW)
        self.assertEqual(result["other_layouts"], 1)
        self.assertEqual(sum(g["sessions"] for g in result["groups"].values()), 0)

    def test_style_classification(self):
        self.assertEqual(insights.classify_style('{"root": {"component": "Steps", "props": {}}}'), "guided")
        self.assertEqual(insights.classify_style('{"root": {"component": "Row", "props": {"density": "compact"}}}'), "compact")
        self.assertIsNone(insights.classify_style('{"root": {"component": "Row", "props": {"density": "comfortable"}}}'))
        self.assertIsNone(insights.classify_style("not json"))
        self.assertIsNone(insights.classify_style('{"root": 5}'))


class ThresholdAndComparisonTests(unittest.TestCase):
    def _fill(self, db, style, engaged, stalled):
        for _ in range(engaged):
            put_session(db, style=style, completed=True, selections=2, nxt=2 if style == "guided" else 0)
        for _ in range(stalled):
            put_session(db, style=style, selections=1)

    def test_ratio_withheld_below_minimum_then_reported(self):
        db = temp_db_path()
        self._fill(db, "guided", 6, 3)  # 9 mature
        self.assertIsNone(group(db, "guided")["ratio"])
        self.assertIn("too few to report a ratio", render_insights(compute_insights(db, NOW)))
        self._fill(db, "guided", 1, 0)  # 10 mature
        self.assertAlmostEqual(group(db, "guided")["ratio"], 0.7)

    def test_group_with_only_stalled_sessions_still_renders(self):
        db = temp_db_path()
        self._fill(db, "compact", 0, 12)       # reportable, but no engaged completion at all
        self._fill(db, "guided", 12, 2)
        result = compute_insights(db, NOW)
        self.assertIsNone(result["groups"]["compact"]["means"])
        self.assertEqual(result["groups"]["compact"]["ratio"], 0.0)
        text = render_insights(result)
        self.assertIn("No engaged completions yet", text)
        self.assertIsNotNone(insights.insights_for_prompt(db, NOW))   # must not silently fail open

    def test_wilson_interval_known_value(self):
        low, high = wilson_interval(5, 10)
        self.assertAlmostEqual(low, 0.2366, places=3)
        self.assertAlmostEqual(high, 0.7634, places=3)

    def test_clear_difference_only_when_intervals_are_disjoint(self):
        db = temp_db_path(); seed("guided_better", db, NOW)
        self.assertEqual(compute_insights(db, NOW)["comparison"], {"state": "clear", "leader": "guided"})
        db = temp_db_path(); seed("compact_better", db, NOW)
        self.assertEqual(compute_insights(db, NOW)["comparison"], {"state": "clear", "leader": "compact"})
        db = temp_db_path(); seed("balanced", db, NOW)
        self.assertEqual(compute_insights(db, NOW)["comparison"]["state"], "none")

    def test_no_comparison_when_one_group_is_thin(self):
        db = temp_db_path()
        self._fill(db, "guided", 12, 4)
        self._fill(db, "compact", 3, 2)
        result = compute_insights(db, NOW)
        self.assertEqual(result["comparison"]["state"], "not_possible")
        self.assertTrue(result["usable"])

    def test_no_usable_history(self):
        db = temp_db_path(); seed("no_history", db, NOW)
        result = compute_insights(db, NOW)
        self.assertFalse(result["usable"])
        self.assertIsNone(insights.insights_for_prompt(db, NOW))

    def test_navigation_is_reported_for_guided_only(self):
        db = temp_db_path(); seed("guided_better", db, NOW)
        text = render_insights(compute_insights(db, NOW))
        self.assertIn("back-steps", text)
        compact_line = next(l for l in text.splitlines() if l.startswith("- compact"))
        self.assertNotIn("back-steps", compact_line)


class WordingTests(unittest.TestCase):
    def test_summary_is_cautious_and_never_claims_abandonment_or_conversion(self):
        db = temp_db_path(); seed("guided_better", db, NOW)
        text = render_insights(compute_insights(db, NOW))
        lowered = text.lower()
        for required in ("observational", "not causal", "provisional completion ratio", "potentially stalled", "not confirmed as abandoned"):
            self.assertIn(required, lowered)
        self.assertNotIn("conversion", lowered)
        self.assertNotIn("abandonment rate", lowered)
        self.assertLess(len(text), 1800)


class DeterminismAndReadOnlyTests(unittest.TestCase):
    def test_same_data_same_text_regardless_of_insert_order(self):
        rows = [dict(style="guided", completed=True, selections=2, nxt=3), dict(style="guided", selections=1),
                dict(style="compact", completed=True, selections=3), dict(style="compact", age=timedelta(minutes=5), selections=1)] * 6
        a, b = temp_db_path(), temp_db_path()
        for r in rows: put_session(a, **r)
        for r in reversed(rows): put_session(b, **r)
        self.assertEqual(render_insights(compute_insights(a, NOW)), render_insights(compute_insights(b, NOW)))
        self.assertEqual(render_insights(compute_insights(a, NOW)), render_insights(compute_insights(a, NOW)))

    def test_compute_never_modifies_or_creates_a_database(self):
        db = temp_db_path(); seed("balanced", db, NOW)
        before = hashlib.sha256(db.read_bytes()).hexdigest(); mtime = db.stat().st_mtime_ns
        compute_insights(db, NOW); insights.insights_for_prompt(db, NOW)
        self.assertEqual(hashlib.sha256(db.read_bytes()).hexdigest(), before)
        self.assertEqual(db.stat().st_mtime_ns, mtime)
        missing = db.parent / "does-not-exist.db"
        self.assertFalse(compute_insights(missing, NOW)["usable"])
        self.assertFalse(missing.exists())

    def test_empty_or_tableless_database_is_handled(self):
        import sqlite3
        db = temp_db_path(); sqlite3.connect(db).close()  # a file with no sessions table
        self.assertFalse(compute_insights(db, NOW)["usable"])


if __name__ == "__main__":
    unittest.main()
