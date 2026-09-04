from __future__ import annotations

import copy
import os
import shutil
import sys
import tempfile
import unittest
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from src.common import ROOT, read_json
from src.generate_issue import _call_openai, _transactional_write, generate
from src.validation import validate_repository


class GenerationTests(unittest.TestCase):
    def test_api_accepts_null_web_search_sources(self) -> None:
        output = {"stories": [{"sources": [{"url": "https://example.com/real"}]}]}
        response = SimpleNamespace(
            output_text=json.dumps(output),
            model_dump=lambda: {"output": [{
                "type": "web_search_call",
                "action": {"sources": None, "url": "https://example.com/real"},
            }]},
        )
        openai = Mock()
        openai.return_value.responses.create.return_value = response
        with patch.dict(sys.modules, {"openai": SimpleNamespace(OpenAI=openai)}):
            self.assertEqual(_call_openai("test-model", "instructions", "request", {}), output)

    def test_api_sources_must_come_from_web_search_results(self) -> None:
        output = {"stories": [{"sources": [{"url": "https://example.com/invented"}]}]}
        response = SimpleNamespace(
            output_text=json.dumps(output),
            model_dump=lambda: {"output": [{"type": "web_search_call", "action": {"sources": [{"url": "https://example.com/real"}]}}]},
        )
        openai = Mock()
        openai.return_value.responses.create.return_value = response
        with patch.dict(sys.modules, {"openai": SimpleNamespace(OpenAI=openai)}):
            with self.assertRaisesRegex(RuntimeError, "OpenAI generation failed"):
                _call_openai("test-model", "instructions", "request", {})
            openai.assert_called_once_with(max_retries=0, timeout=300.0)

    def test_api_image_url_must_come_from_web_search_results(self) -> None:
        output = {
            "stories": [{
                "sources": [{"url": "https://example.com/article"}],
                "image": {
                    "url": "https://cdn.example.com/unverified.jpg",
                    "rightsUrl": "https://example.com/rights",
                },
            }]
        }
        response = SimpleNamespace(
            output_text=json.dumps(output),
            model_dump=lambda: {"output": [{"type": "web_search_call", "action": {"sources": [
                {"url": "https://example.com/article"},
                {"url": "https://example.com/rights"},
            ]}}]},
        )
        openai = Mock()
        openai.return_value.responses.create.return_value = response
        with patch.dict(sys.modules, {"openai": SimpleNamespace(OpenAI=openai)}):
            with self.assertRaisesRegex(RuntimeError, "OpenAI generation failed"):
                _call_openai("test-model", "instructions", "request", {})

    def test_transaction_rolls_back_if_promotion_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = root / "first.json"
            second = root / "second.json"
            first.write_text('{"old": 1}\n', encoding="utf-8")
            second.write_text('{"old": 2}\n', encoding="utf-8")
            before = {first: first.read_bytes(), second: second.read_bytes()}
            real_replace = os.replace
            promotion_count = 0

            def fail_second_promotion(source: object, destination: object) -> None:
                nonlocal promotion_count
                if Path(destination) in before:
                    promotion_count += 1
                    if promotion_count == 2:
                        raise OSError("simulated promotion failure")
                real_replace(source, destination)

            with patch("src.generate_issue.os.replace", side_effect=fail_second_promotion):
                with self.assertRaises(OSError):
                    _transactional_write({first: {"new": 1}, second: {"new": 2}})
            self.assertEqual(first.read_bytes(), before[first])
            self.assertEqual(second.read_bytes(), before[second])

    def test_existing_day_appends_without_overwriting(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for directory in ("config", "i18n", "prompts", "content"):
                shutil.copytree(ROOT / directory, root / directory)
            original = read_json(root / "content" / "2024-01-26.json")
            new_story = copy.deepcopy(original["stories"][1])
            new_story["id"] = new_story["slug"] = "changed-train-platform"
            new_story["brief"] = "A commuter finds that a train will leave from another platform, asks a staff member for directions, and reaches it on time."
            new_story["everydayMeta"]["domain"] = "public_transport"
            new_story["everydayMeta"]["scenario"] = "changed_train_platform"
            seed = {key: value for key, value in new_story.items() if key != "levels"}
            adaptation = {"id": new_story["id"], "levels": new_story["levels"]}
            with patch.dict(os.environ, {"OPENAI_MODEL": "test-model"}), patch(
                "src.generate_issue._call_openai",
                side_effect=[{"stories": [seed]}, {"adaptations": [adaptation]}],
            ):
                result = generate(root, "2024-01-26", 1)
            self.assertEqual([story["id"] for story in result["stories"][:3]], [story["id"] for story in original["stories"]])
            self.assertEqual(result["stories"][-1]["id"], "changed-train-platform")
            self.assertEqual(len(result["stories"]), 4)
            self.assertEqual(validate_repository(root), [])

    def test_append_keeps_an_old_issues_levels_after_config_expands(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for directory in ("config", "i18n", "prompts", "content"):
                shutil.copytree(ROOT / directory, root / directory)
            levels_path = root / "config" / "reading-levels.json"
            levels_payload = read_json(levels_path)
            new_level = copy.deepcopy(levels_payload["levels"][-1])
            new_level.update({"id": "gimel", "label": "ג", "name": "Gimel"})
            levels_payload["levels"].append(new_level)
            levels_path.write_text(json.dumps(levels_payload), encoding="utf-8")
            original = read_json(root / "content" / "2024-01-26.json")
            new_story = copy.deepcopy(original["stories"][1])
            new_story["id"] = new_story["slug"] = "pharmacy-closing-time"
            new_story["brief"] = "A customer notices the pharmacy is about to close, calls ahead, and arrives in time to collect a reserved item."
            new_story["everydayMeta"]["domain"] = "pharmacy"
            new_story["everydayMeta"]["scenario"] = "collect_before_closing"
            seed = {key: value for key, value in new_story.items() if key != "levels"}
            adaptation = {"id": new_story["id"], "levels": new_story["levels"]}
            with patch.dict(os.environ, {"OPENAI_MODEL": "test-model"}), patch(
                "src.generate_issue._call_openai",
                side_effect=[{"stories": [seed]}, {"adaptations": [adaptation]}],
            ):
                result = generate(root, "2024-01-26", 1)
            self.assertEqual(result["availableLevels"], ["alef", "alefPlus", "bet"])
            self.assertNotIn("gimel", result["stories"][-1]["levels"])

    def test_invalid_research_is_retried_before_adaptation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for directory in ("config", "i18n", "prompts", "content"):
                shutil.copytree(ROOT / directory, root / directory)
            original = read_json(root / "content" / "2024-01-26.json")
            new_story = copy.deepcopy(original["stories"][1])
            new_story["id"] = new_story["slug"] = "changed-train-platform"
            new_story["brief"] = "A commuter follows a changed platform announcement and reaches the train on time."
            new_story["everydayMeta"]["domain"] = "public_transport"
            new_story["everydayMeta"]["scenario"] = "changed_train_platform"
            valid_seed = {key: value for key, value in new_story.items() if key != "levels"}
            invalid_seed = {**valid_seed, "slug": "Not a valid slug"}
            adaptation = {"id": new_story["id"], "levels": new_story["levels"]}
            call = Mock(side_effect=[
                {"stories": [invalid_seed]},
                {"stories": [valid_seed]},
                {"adaptations": [adaptation]},
            ])
            with patch.dict(os.environ, {"OPENAI_MODEL": "test-model"}), patch(
                "src.generate_issue._call_openai",
                call,
            ):
                result = generate(root, "2024-01-26", 1)
            self.assertEqual(call.call_count, 3)
            self.assertEqual(result["stories"][-1]["id"], "changed-train-platform")


if __name__ == "__main__":
    unittest.main()
