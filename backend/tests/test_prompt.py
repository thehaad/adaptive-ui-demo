import os
import re
import types
import unittest
from unittest import mock

from fastapi.testclient import TestClient

import insights
import layout_ai
import main
from layout_ai import GeneratedLayout, SYSTEM_PROMPT, generate_layout, insights_system_block
from tests.support import NOW, configured_db, put_session, temp_db_path
from tools.seed_synthetic import seed

DONE = {"label": "Finish", "action": "complete_onboarding"}
GOOD = {"component": "Row", "props": {"direction": "row", "breakpoint": 700, "density": "compact"},
        "children": [{"component": "PreferenceSelector", "props": {"label": "Level", "optionSet": "experience_level"}}], "completion": DONE}
BAD = {"component": "Row", "props": {"direction": "row", "breakpoint": 700, "density": "compact"},
       "children": [{"component": "PreferenceSelector", "props": {"label": "a", "optionSet": "workout_focus"}},
                    {"component": "PreferenceSelector", "props": {"label": "b", "optionSet": "workout_focus"}}], "completion": DONE}


def fake_client(roots):
    calls = []
    def parse(**kwargs):
        calls.append(kwargs)
        out = GeneratedLayout.model_validate({"root": roots[len(calls) - 1]})
        return types.SimpleNamespace(parsed_output=out, stop_reason="end_turn",
                                     content=[types.SimpleNamespace(type="text", text=out.model_dump_json())])
    return types.SimpleNamespace(messages=types.SimpleNamespace(parse=parse)), calls


class PromptContentTests(unittest.TestCase):
    def test_without_insights_the_request_is_unchanged(self):
        client, calls = fake_client([GOOD])
        generate_layout("anything", client)
        self.assertEqual(calls[0]["system"], SYSTEM_PROMPT)

    def test_insights_arrive_as_a_second_system_block_with_usage_rules(self):
        db = temp_db_path(); seed("guided_better", db, NOW)
        text = insights.insights_for_prompt(db, NOW)
        client, calls = fake_client([GOOD])
        generate_layout("anything", client, insights=text)
        system = calls[0]["system"]
        self.assertEqual([b["type"] for b in system], ["text", "text"])
        self.assertEqual(system[0]["text"], SYSTEM_PROMPT)               # base prompt untouched
        block = system[1]["text"]
        self.assertEqual(block, insights_system_block(text))
        for rule in ("ALWAYS takes priority", "tie-breaker", "not causal", "Never mention these statistics"):
            self.assertIn(rule, block)
        self.assertIn("83%", block)                                       # the aggregate evidence itself

    def test_no_raw_session_content_reaches_claude(self):
        db = temp_db_path()
        sentinel = "SENTINEL-private-goal-7731"
        ids = []
        for i in range(12):
            ids.append(put_session(db, style="guided", completed=True, selections=2, nxt=3, preference=f"[SYNTHETIC] {sentinel} {i}"))
            ids.append(put_session(db, style="compact", selections=1, preference=f"[SYNTHETIC] {sentinel} c{i}"))
        text = insights.insights_for_prompt(db, NOW)
        self.assertIsNotNone(text)
        client, calls = fake_client([GOOD])
        generate_layout("ordinary request", client, insights=text)
        sent = repr(calls[0]["system"]) + repr(calls[0]["messages"][0]["content"])
        self.assertNotIn(sentinel, sent)
        for session_id in ids:
            self.assertNotIn(session_id, sent)
        self.assertIsNone(re.search(r"20\d\d-\d\d-\d\dT", repr(calls[0]["system"])))   # no timestamps
        self.assertIsNone(re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-", repr(calls[0]["system"])))  # no uuids
        self.assertNotIn("ai-synthetic", repr(calls[0]["system"]))                        # no layout ids

    def test_validation_and_retry_still_apply_with_insights(self):
        db = temp_db_path(); seed("guided_better", db, NOW)
        text = insights.insights_for_prompt(db, NOW)
        client, calls = fake_client([BAD, GOOD])
        layout = generate_layout("anything", client, insights=text)
        self.assertEqual(len(calls), 2)
        self.assertIn("used 2 times", calls[1]["messages"][-1]["content"])
        self.assertTrue(all(len(c["system"]) == 2 for c in calls))
        self.assertEqual(layout["root"]["children"][-1]["component"], "ActionButton")


class FailOpenTests(unittest.TestCase):
    def test_corrupt_database_means_no_insights(self):
        db = temp_db_path(); db.write_bytes(b"this is not a sqlite file" * 50)
        with self.assertLogs("insights", level="WARNING"):
            self.assertIsNone(insights.insights_for_prompt(db, NOW))

    def test_kill_switch(self):
        db = temp_db_path(); seed("guided_better", db, NOW)
        with mock.patch.dict(os.environ, {"ADAPTIVEUI_INSIGHTS": "off"}):
            self.assertIsNone(insights.insights_for_prompt(db, NOW))
        self.assertIsNotNone(insights.insights_for_prompt(db, NOW))


class EndpointTests(unittest.TestCase):
    """The real personalize endpoint, a mocked model, and isolated databases."""

    def post(self, db):
        client, calls = fake_client([GOOD])
        with configured_db(db), mock.patch.object(layout_ai.anthropic, "Anthropic", lambda: client):
            response = TestClient(main.app).post("/api/layout/personalize", json={"preference": "I want to get fitter"})
        return response, calls

    def test_history_present_adds_the_block(self):
        db = temp_db_path(); seed("compact_better", db, __import__("datetime").datetime.now(__import__("datetime").timezone.utc))
        response, calls = self.post(db)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(calls[0]["system"]), 2)
        self.assertIn("compact", calls[0]["system"][1]["text"])

    def test_no_usable_history_leaves_composition_unchanged(self):
        db = temp_db_path()  # does not exist
        response, calls = self.post(db)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(calls[0]["system"], SYSTEM_PROMPT)
        self.assertFalse(db.exists())  # reading history never creates the database

    def test_broken_history_does_not_break_onboarding(self):
        db = temp_db_path(); db.write_bytes(b"garbage" * 100)
        with self.assertLogs("insights", level="WARNING"):
            response, calls = self.post(db)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(calls[0]["system"], SYSTEM_PROMPT)


if __name__ == "__main__":
    unittest.main()
