from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from src.common import ROOT, read_json, load_level_config, write_json
from src.editions import to_editions, build_index
from src.generate_issue import _call_openai, _updated_history, generate
from src.generation_state import GenerationState, ResearchBudgetExhausted, current_state, generation_session
from src.validation import validate_repository


class GenerationStateTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        for folder in ("config", "prompts"):
            shutil.copytree(ROOT / folder, self.root / folder)
        self.day = "2024-01-26"
        self.env = patch.dict(os.environ, OPENAI_MODEL="test-model")
        self.env.start()
        self.addCleanup(self.env.stop)

    def session(self, **kwargs):
        return generation_session(self.root, self.day, 3, "test-model", **kwargs)

    def response(self, count, result=None):
        return SimpleNamespace(output_text=json.dumps(result or {"stories": []}),
                               model_dump=lambda: {"output": [{"type": "web_search_call"}] * count})

    def test_total_discovery_and_response_limits_reach_the_api(self):
        client = Mock()
        client.return_value.responses.create.side_effect = lambda **kw: self.response(kw["max_tool_calls"])
        with self.session() as state, patch.dict(sys.modules, {"openai": SimpleNamespace(OpenAI=client)}), redirect_stdout(StringIO()):
            for phase in ("Sourced discovery 1", "Sourced discovery 2"):
                _call_openai("test-model", "instructions", phase, {}, phase=phase)
            with self.assertRaises(ResearchBudgetExhausted):
                _call_openai("test-model", "instructions", "extra", {}, phase="Sourced discovery 3")
            for phase in ("HISTORY research 1", "HISTORY research 2"):
                _call_openai("test-model", "instructions", phase, {}, phase=phase)
            with self.assertRaises(ResearchBudgetExhausted):
                _call_openai("test-model", "instructions", "extra", {}, phase="HISTORY research 3")
            self.assertEqual(state.data["searches"], 25)
        self.assertEqual([call.kwargs["max_tool_calls"] for call in client.return_value.responses.create.call_args_list], [8, 2, 8, 7])
        self.assertTrue(all(call.kwargs["max_retries"] == 0 for call in client.call_args_list))

    def test_resume_reuses_results_without_requests_or_extra_search_charges(self):
        client = Mock()
        client.return_value.responses.create.return_value = self.response(2, {"stories": [{"sources": [{"url": "https://example.com/unverified"}]}]})
        with patch.dict(sys.modules, {"openai": SimpleNamespace(OpenAI=client)}), redirect_stdout(StringIO()):
            with self.session():
                first = _call_openai("test-model", "instructions", "request", {}, phase="HISTORY research 1")
                first["stories"].clear()
            with self.session(resume=True) as state:
                restored = _call_openai("test-model", "instructions", "request", {}, phase="HISTORY research 1")
                self.assertEqual(len(restored["stories"]), 1)
                self.assertEqual(restored["_provenanceErrors"], ["https://example.com/unverified"])
                self.assertEqual(state.data["searches"], 2)
        self.assertEqual(client.return_value.responses.create.call_count, 1)

    def test_unknown_request_usage_keeps_reserved_budget_on_resume(self):
        client = Mock()
        client.return_value.responses.create.side_effect = RuntimeError("connection lost")
        with self.session(), patch.dict(sys.modules, {"openai": SimpleNamespace(OpenAI=client)}), redirect_stdout(StringIO()):
            with self.assertRaises(RuntimeError):
                _call_openai("test-model", "instructions", "request", {}, phase="HISTORY research 1")
        with self.session(resume=True) as state:
            self.assertEqual(state.data["searches"], 8)
            self.assertEqual(state.data["responses"], {})

    def test_resume_replays_failed_branch_before_later_saved_success(self):
        client = Mock()
        client.return_value.responses.create.side_effect = [RuntimeError("lost connection"), self.response(1)]
        with patch.dict(sys.modules, {"openai": SimpleNamespace(OpenAI=client)}), redirect_stdout(StringIO()):
            for resume in (False, True):
                with self.session(resume=resume) as state:
                    with self.assertRaises(RuntimeError):
                        _call_openai("test-model", "instructions", "first", {}, phase="Sourced discovery 1")
                    self.assertEqual(_call_openai("test-model", "instructions", "second", {}, phase="Sourced discovery 2"), {"stories": []})
                    self.assertEqual(state.data["searches"], 9)
        self.assertEqual(client.return_value.responses.create.call_count, 2)

    def test_resume_rejects_changed_settings_and_content(self):
        with self.assertRaisesRegex(ValueError, "No generation checkpoint"):
            with self.session(resume=True):
                pass
        with self.session():
            pass
        with self.assertRaisesRegex(ValueError, "does not match"):
            GenerationState(self.root, self.day, 3, "another-model", resume=True)
        settings = self.root / "prompts/editorial.md"
        original = settings.read_text()
        settings.write_text(original + "\nNew settings.\n")
        with self.assertRaisesRegex(ValueError, "does not match"):
            with self.session(resume=True):
                pass
        settings.write_text(original)
        write_json(self.root / "content/index.json", {"changed": True})
        with self.assertRaisesRegex(ValueError, "changed since"):
            with self.session(resume=True):
                pass

    def test_resume_restores_completed_issue_after_write_failure_without_generation(self):
        legacy = read_json(ROOT / "tests/fixtures/legacy-issue.json")
        issue = to_editions(legacy)
        payloads = {self.root / "content" / f"{self.day}.json": issue,
                    self.root / "content/index.json": build_index({self.day: issue}, load_level_config()),
                    self.root / "content/everyday-history.json": _updated_history(
                        {"schemaVersion": 1, "items": []}, legacy["stories"], self.day)}

        def interrupted(*args):
            current_state.get().stage(payloads)
            raise RuntimeError("interrupted before content write")

        with patch("src.generate_issue._generate", side_effect=interrupted), redirect_stdout(StringIO()):
            with self.assertRaisesRegex(RuntimeError, "interrupted"):
                generate(self.root, self.day, 3)
        with patch("src.generate_issue._generate") as generation, redirect_stdout(StringIO()):
            self.assertEqual(generate(self.root, self.day, 3, resume=True), issue)
            # Resume after the files have already been saved is also safe.
            self.assertEqual(generate(self.root, self.day, 3, resume=True), issue)
            generation.assert_not_called()
        self.assertEqual(validate_repository(self.root), [])

    def test_exhausted_history_budget_keeps_supported_current_article(self):
        legacy = read_json(ROOT / "tests/fixtures/legacy-issue.json")
        news = next(story for story in legacy["stories"] if story["type"] == "current")
        history = next(story for story in legacy["stories"] if story["type"] == "history")
        site_path = self.root / "config/site.json"
        site = read_json(site_path)
        site.update(defaultIssueStoryCount=2, minimumIssueStoryCount=1, maximumIssueStoryCount=2)
        write_json(site_path, site)
        candidates = [{key: story[key] for key in ("id", "type", "category", "brief", "sources")}
                      | {"historyFamily": "current" if story["type"] == "current" else "culture",
                         "discoverySource": "current" if story["type"] == "current" else "wikimedia"}
                      for story in (news, history)]

        def respond(*args, **kwargs):
            phase = kwargs["phase"]
            if "duplicate review" in phase:
                return {"verdicts": [{"candidateId": story["id"] + "-" + self.day,
                         "isDuplicate": False, "isEmptyCurrent": False, "isNonLocalCurrent": False,
                         "matchedStoryId": None, "reason": "unique"} for story in candidates]}
            if phase.startswith("Sourced discovery"):
                return {"stories": candidates}
            if phase.startswith("HISTORY research"):
                raise ResearchBudgetExhausted("budget spent")
            self.fail(f"Unexpected paid call: {phase}")

        def adapt(seed, *args):
            return {**seed, "levels": news["levels"]}

        with patch("src.generate_issue.CURRENT_TARGET", 1), patch("src.generate_issue.HISTORY_TARGET", 1), patch(
            "src.generate_issue._generated_story_target", return_value=0,
        ), patch("src.generate_issue._call_openai", side_effect=respond), patch(
            "src.generate_issue._adapt_editions", side_effect=adapt,
        ), redirect_stdout(StringIO()):
            issue = generate(self.root, self.day, 3)
        for edition in issue["editions"].values():
            self.assertEqual([story["type"] for story in edition["stories"]], ["current"])
        self.assertEqual(validate_repository(self.root), [])


if __name__ == "__main__":
    unittest.main()
