import sqlite3
import unittest
from unittest import mock

import insights
import tools.seed_synthetic as seed_tool
from layout_validation import validate_layout
from sessions import default_db_path
from tests.support import NOW, temp_db_path
from tools.seed_synthetic import SCENARIOS, SYNTHETIC_LAYOUT_PREFIX, SYNTHETIC_PREFERENCE, layout_for, refuse_reason, seed


class ScenarioTests(unittest.TestCase):
    def test_each_scenario_has_the_intended_signal(self):
        expected = {"guided_better": ("clear", "guided", True), "compact_better": ("clear", "compact", True),
                    "balanced": ("none", None, True), "no_history": ("not_possible", None, False)}
        for name, (state, leader, usable) in expected.items():
            db = temp_db_path(); seed(name, db, NOW)
            result = insights.compute_insights(db, NOW)
            self.assertEqual((result["comparison"]["state"], result["comparison"]["leader"], result["usable"]), (state, leader, usable), name)

    def test_every_row_is_clearly_labeled_synthetic(self):
        for name in SCENARIOS:
            db = temp_db_path(); seed(name, db, NOW)
            rows = sqlite3.connect(db).execute("SELECT preference, layout_id, layout_source FROM sessions").fetchall()
            self.assertTrue(rows)
            for preference, layout_id, source in rows:
                self.assertTrue(preference.startswith(SYNTHETIC_PREFERENCE))
                self.assertTrue(layout_id.startswith(SYNTHETIC_LAYOUT_PREFIX))
                self.assertEqual(source, "ai")

    def test_generation_is_deterministic(self):
        a, b = temp_db_path(), temp_db_path()
        seed("balanced", a, NOW); seed("balanced", b, NOW)
        dump = lambda p: sqlite3.connect(p).execute("SELECT * FROM sessions ORDER BY id").fetchall()
        self.assertEqual(dump(a), dump(b))

    def test_synthetic_layouts_obey_the_real_validator(self):
        for style in ("guided", "compact"):
            for i in range(3):
                self.assertEqual(validate_layout(layout_for(style, i)), [], (style, i))


class SafetyTests(unittest.TestCase):
    def test_refuses_the_default_development_database_path(self):
        self.assertIn("default development database", refuse_reason(default_db_path()))  # path comparison only

    def test_main_refuses_before_writing_anything(self):
        stand_in = temp_db_path()  # a stand-in for the default path: never the real one
        with mock.patch.object(seed_tool, "default_db_path", lambda: stand_in):
            with self.assertRaises(SystemExit) as raised:
                seed_tool.main(["--scenario", "balanced", "--db", str(stand_in)])
        self.assertIn("refusing", str(raised.exception))
        self.assertFalse(stand_in.exists())

    def test_refuses_a_database_that_holds_real_sessions(self):
        from tests.support import put_session
        db = temp_db_path()
        put_session(db, source="static", preference=None, completed=True, selections=1)  # not synthetic
        self.assertIn("non-synthetic", refuse_reason(db))
        with self.assertRaises(SystemExit):
            seed("balanced", db, NOW)
        self.assertEqual(sqlite3.connect(db).execute("SELECT COUNT(*) FROM sessions").fetchone()[0], 1)

    def test_may_extend_an_all_synthetic_database(self):
        db = temp_db_path(); seed("no_history", db, NOW)
        self.assertIsNone(refuse_reason(db))


if __name__ == "__main__":
    unittest.main()
