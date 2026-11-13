from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.generate_issue import generate, _log, _log_prompt, _log_validation_errors
from src.generation_state import current_state
from src.generation_summary import EVENT_LIMIT, record_targets
from src.generation_usage import record_usage


class GenerationSummaryTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.day = "2026-11-13"
        self.folder = self.root / "build/generation-summary"

    def report(self):
        return json.loads((self.folder / f"{self.day}.json").read_text())

    def run_generation(self, action):
        with patch("src.generate_issue._generate", side_effect=action), redirect_stdout(StringIO()):
            return generate(self.root, self.day, 0)

    def test_success_captures_shortfall_counts_usage_and_excludes_prompts(self):
        issue = {"editions": {"alef": {"stories": [{"type": "history", "id": "singing"}]},
                              "bet": {"stories": []}}}

        def action(*args):
            record_targets(mode="new issue", history=3)
            _log_prompt("Sourced discovery attempt 1/3", "PRIVATE PROMPT", "omitting PRIVATE ARTICLE")
            _log("Sourced discovery attempt 1/3: returned candidates by type: {\"history\": 1}")
            _log("Sourced discovery attempt 3/3: discovery budget exhausted; keeping selected subjects")
            state = current_state.get()
            state.data["searches"] = 12
            state.data["discoverySearches"] = 10
            record_usage("gpt-6-luna", "Sourced discovery attempt 1/3", {
                "usage": {"input_tokens": 1000, "output_tokens": 200,
                          "input_tokens_details": {"cached_tokens": 0},
                          "output_tokens_details": {"reasoning_tokens": 100}},
                "output": [{"type": "web_search_call"}] * 9,
            }, _log)
            return issue

        self.assertEqual(self.run_generation(action), issue)
        report = self.report()
        self.assertEqual(report["status"], "success")
        self.assertEqual(report["targets"]["history"], 3)
        self.assertEqual(report["editions"]["alef"]["counts"]["history"], 1)
        self.assertEqual(report["editions"]["bet"]["total"], 0)
        self.assertEqual(report["budget"]["usedOrReserved"], 12)
        self.assertEqual(report["usage"]["requests"], 1)
        self.assertEqual(report["researchRequests"][0]["web_search_calls"], 9)
        for path in self.folder.iterdir():
            self.assertNotIn("PRIVATE", path.read_text())
        markdown = (self.folder / f"{self.day}.md").read_text()
        self.assertIn("discovery budget exhausted", markdown)
        self.assertIn("12/25", markdown)
        self.assertIn("| alef | 1 | 0 | 1 |", markdown)

    def test_failure_preserves_original_error_and_unknown_usage(self):
        def action(*args):
            _log_validation_errors("HISTORY research round 1", ["subject: insufficient facts"])
            record_usage("unknown-model", "HISTORY research round 1", None, _log)
            raise RuntimeError("private exception details")

        with self.assertRaisesRegex(RuntimeError, "private exception details"):
            self.run_generation(action)
        report = self.report()
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["errorType"], "RuntimeError")
        self.assertEqual(report["usage"]["unpriced_requests"], 1)
        self.assertFalse(report["usage"]["usage_complete"])
        self.assertIn("subject: insufficient facts", " ".join(report["research"]))
        self.assertNotIn("private exception", json.dumps(report))

    def test_report_is_bounded_and_omissions_survive_many_warnings(self):
        def action(*args):
            for number in range(100):
                _log(f"Adaptation {number}: quality warning; " + "x" * 1000)
            _log("Adaptation final: omitting story failed-history after content retries")
            return None

        self.run_generation(action)
        report = self.report()
        self.assertEqual(len(report["diagnostics"]), EVENT_LIMIT)
        self.assertEqual(report["omittedEvents"]["diagnostics"], 100 - EVENT_LIMIT)
        self.assertEqual(len(report["omissions"]), 1)
        self.assertEqual(report["status"], "no-change")
        self.assertLess(len(json.dumps(report)), 30000)
        self.run_generation(lambda *args: None)
        self.assertEqual(self.report()["diagnostics"], [])

    def test_resume_setup_failure_still_saves_report(self):
        with self.assertRaises(ValueError), redirect_stdout(StringIO()):
            generate(self.root, self.day, 0, resume=True)
        self.assertTrue(self.report()["resume"])
        self.assertEqual(self.report()["status"], "failed")
        self.assertEqual(self.report()["usage"]["requests"], 0)

    def test_report_write_failure_does_not_fail_generation(self):
        with patch("src.generation_summary.Path.mkdir", side_effect=OSError("unwritable")), \
                patch("src.generate_issue.generation_session") as session:
            session.return_value.__enter__.return_value.data = {
                "completed": None, "searches": 0, "discoverySearches": 0,
            }
            self.assertIsNone(self.run_generation(lambda *args: None))
