from __future__ import annotations

import copy
import os
import shutil
import sys
import tempfile
import unittest
import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from src.common import ROOT, read_json, units_text
from src.generate_issue import (
    PROVENANCE_ERRORS_KEY,
    _segmentation_preservation_errors,
    _call_openai,
    _remove_redundant_sources,
    _recent_issue_context,
    _safe_log_text,
    _seed_errors,
    _transactional_write,
    generate,
)
from src.validation import validate_repository


def _plain_adaptation(story: dict) -> dict:
    return {
        "id": story["id"],
        "levels": {
            level_id: {
                "title": units_text(level["title"]),
                "teaser": units_text(level["teaser"]),
                "paragraphs": [units_text(paragraph) for paragraph in level["paragraphs"]],
            }
            for level_id, level in story["levels"].items()
        },
    }


def _segmentation(story: dict) -> dict:
    return {
        "id": story["id"],
        "levels": {
            level_id: {
                "title": [{"text": unit["text"], "type": unit["type"]} for unit in level["title"]],
                "teaser": [{"text": unit["text"], "type": unit["type"]} for unit in level["teaser"]],
                "paragraphs": [
                    [{"text": unit["text"], "type": unit["type"]} for unit in paragraph]
                    for paragraph in level["paragraphs"]
                ],
            }
            for level_id, level in story["levels"].items()
        },
    }


def _translations(story: dict) -> dict:
    return {
        "id": story["id"],
        "levels": {
            level_id: {
                "title": [unit["translations"] for unit in level["title"]],
                "teaser": [unit["translations"] for unit in level["teaser"]],
                "paragraphs": [
                    [unit["translations"] for unit in paragraph]
                    for paragraph in level["paragraphs"]
                ],
            }
            for level_id, level in story["levels"].items()
        },
    }


class GenerationTests(unittest.TestCase):
    def test_recent_issue_context_uses_only_previous_three_days(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            content_dir = Path(temporary)
            for issue_date in ("2026-09-01", "2026-09-02", "2026-09-04", "2026-09-05"):
                payload = {
                    "stories": [{
                        "id": f"story-{issue_date}",
                        "type": "current",
                        "category": "city",
                        "brief": f"Brief for {issue_date}",
                    }]
                }
                (content_dir / f"{issue_date}.json").write_text(json.dumps(payload), encoding="utf-8")
            context = _recent_issue_context(content_dir, date.fromisoformat("2026-09-05"), 3)
        self.assertEqual([item["date"] for item in context], ["2026-09-04", "2026-09-02"])

    def test_new_issue_requires_three_to_five_everyday_stories(self) -> None:
        site = read_json(ROOT / "config" / "site.json")
        levels = read_json(ROOT / "config" / "reading-levels.json")["levels"]
        seeds = [
            {
                "id": f"story-{index}",
                "slug": f"story-{index}",
                "type": "history" if index >= 8 else "current",
                "category": "history" if index >= 8 else "city",
                "brief": f"Distinct factual subject number {index}",
                "everydayMeta": None,
                "sources": [],
                "image": None,
            }
            for index in range(10)
        ]
        errors = _seed_errors(
            seeds,
            "2026-09-05",
            [level["id"] for level in levels],
            site["translationLocales"],
            site,
            levels,
            None,
            8,
            12,
        )
        self.assertTrue(any("requires 3–5 EVERYDAY" in error for error in errors), errors)

    def test_log_text_escapes_control_characters(self) -> None:
        self.assertEqual(
            _safe_log_text("https://example.com/path\n::error::spoof\x1b\u2028\u202e"),
            "https://example.com/path\\x0a::error::spoof\\x1b\\u2028\\u202e",
        )

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

    def test_api_marks_unverified_sources_for_discarding(self) -> None:
        output = {"stories": [{"sources": [{"url": "https://example.com/invented"}]}]}
        response = SimpleNamespace(
            output_text=json.dumps(output),
            model_dump=lambda: {"output": [{"type": "web_search_call", "action": {"sources": [{"url": "https://example.com/real"}]}}]},
        )
        openai = Mock()
        openai.return_value.responses.create.return_value = response
        with patch.dict(sys.modules, {"openai": SimpleNamespace(OpenAI=openai)}):
            result = _call_openai("test-model", "instructions", "request", {})
        self.assertEqual(result[PROVENANCE_ERRORS_KEY], ["https://example.com/invented"])
        openai.assert_called_once_with(max_retries=2, timeout=300.0)

    def test_redundant_sources_are_removed_when_a_unique_source_remains(self) -> None:
        stories = [
            {
                "sources": [
                    {"url": "https://example.com/shared"},
                    {"url": "https://example.com/shared/"},
                ],
                "image": None,
            },
            {
                "sources": [
                    {"url": "https://example.com/shared?utm_source=test"},
                    {"url": "https://example.com/unique"},
                ],
                "image": {
                    "sourceUrl": "https://example.com/shared",
                    "url": "https://cdn.example.com/removed.jpg",
                    "rightsUrl": "https://example.com/removed-rights",
                },
            },
        ]
        removed_sources, removed_images = _remove_redundant_sources(
            stories,
            None,
            ["https://example.com/shared"],
        )
        self.assertEqual((removed_sources, removed_images), (3, 1))
        self.assertEqual(stories[0]["sources"], [])
        self.assertEqual([source["url"] for source in stories[1]["sources"]], ["https://example.com/unique"])
        self.assertIsNone(stories[1]["image"])

    def test_api_marks_unverified_image_for_discarding(self) -> None:
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
            result = _call_openai("test-model", "instructions", "request", {})
        self.assertEqual(result[PROVENANCE_ERRORS_KEY], ["https://cdn.example.com/unverified.jpg"])

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
            prose = _plain_adaptation(new_story)
            segmentation = _segmentation(new_story)
            translations = _translations(new_story)
            with patch.dict(os.environ, {"OPENAI_MODEL": "test-model"}), patch(
                "src.generate_issue._call_openai",
                side_effect=[
                    {"stories": [seed]},
                    {"adaptations": [prose]},
                    {"adaptations": [segmentation]},
                    {"translations": [translations]},
                ],
            ):
                result = generate(root, "2024-01-26", 1)
            self.assertEqual([story["id"] for story in result["stories"][:3]], [story["id"] for story in original["stories"]])
            self.assertEqual(result["stories"][-1]["id"], "changed-train-platform")
            self.assertEqual(len(result["stories"]), 4)
            self.assertTrue(all(unit["text"] for level in result["stories"][-1]["levels"].values() for unit in level["title"]))
            self.assertEqual(validate_repository(root), [])

    def test_failed_adaptation_request_retries_without_research(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for directory in ("config", "i18n", "prompts", "content"):
                shutil.copytree(ROOT / directory, root / directory)
            original = read_json(root / "content" / "2024-01-26.json")
            new_story = copy.deepcopy(original["stories"][1])
            new_story["id"] = new_story["slug"] = "changed-train-platform"
            new_story["brief"] = "A commuter follows a platform change and reaches the train on time."
            new_story["everydayMeta"]["domain"] = "public_transport"
            new_story["everydayMeta"]["scenario"] = "changed_train_platform"
            seed = {key: value for key, value in new_story.items() if key != "levels"}
            prose = _plain_adaptation(new_story)
            segmentation = _segmentation(new_story)
            translations = _translations(new_story)
            call = Mock(side_effect=[
                {"stories": [seed]},
                RuntimeError("OpenAI generation failed (APIConnectionError)"),
                {"adaptations": [prose]},
                {"adaptations": [segmentation]},
                {"translations": [translations]},
            ])
            with patch.dict(os.environ, {"OPENAI_MODEL": "test-model"}), patch(
                "src.generate_issue._call_openai",
                call,
            ):
                result = generate(root, "2024-01-26", 1)
            self.assertEqual(call.call_count, 5)
            self.assertEqual(call.call_args_list[0].kwargs["phase"], "Research attempt 1/3")
            self.assertEqual(call.call_args_list[1].kwargs["phase"], "Hebrew prose batch 1/1, attempt 1/2")
            self.assertEqual(call.call_args_list[2].kwargs["phase"], "Hebrew prose batch 1/1, attempt 2/2")
            self.assertEqual(call.call_args_list[3].kwargs["phase"], "Segmentation batch 1/1, attempt 1/2")
            self.assertEqual(call.call_args_list[4].kwargs["phase"], "Translation batch 1/1, attempt 1/2")
            self.assertEqual(result["stories"][-1]["id"], "changed-train-platform")

    def test_annotation_accepts_partial_translation_above_coverage_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for directory in ("config", "i18n", "prompts", "content"):
                shutil.copytree(ROOT / directory, root / directory)
            original = read_json(root / "content" / "2024-01-26.json")
            new_story = copy.deepcopy(original["stories"][1])
            new_story["id"] = new_story["slug"] = "changed-office-meeting"
            new_story["brief"] = "A colleague asks to move a meeting and the team agrees on another time."
            new_story["everydayMeta"]["domain"] = "work"
            new_story["everydayMeta"]["scenario"] = "reschedule_office_meeting"
            seed = {key: value for key, value in new_story.items() if key != "levels"}
            levels = copy.deepcopy(new_story["levels"])
            levels["alef"]["title"][0]["translations"]["ru"] = ""
            prose = _plain_adaptation(new_story)
            segmentation = _segmentation(new_story)
            translated_story = {**new_story, "levels": levels}
            translations = _translations(translated_story)
            call = Mock(side_effect=[
                {"stories": [seed]},
                {"adaptations": [prose]},
                {"adaptations": [segmentation]},
                {"translations": [translations]},
            ])
            with patch.dict(os.environ, {"OPENAI_MODEL": "test-model"}), patch(
                "src.generate_issue._call_openai",
                call,
            ):
                result = generate(root, "2024-01-26", 1)
            self.assertEqual(call.call_count, 4)
            self.assertEqual(result["stories"][-1]["levels"]["alef"]["title"][0]["translations"]["ru"], "")
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
            prose = _plain_adaptation(new_story)
            segmentation = _segmentation(new_story)
            translations = _translations(new_story)
            with patch.dict(os.environ, {"OPENAI_MODEL": "test-model"}), patch(
                "src.generate_issue._call_openai",
                side_effect=[
                    {"stories": [seed]},
                    {"adaptations": [prose]},
                    {"adaptations": [segmentation]},
                    {"translations": [translations]},
                ],
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
            new_story = copy.deepcopy(original["stories"][0])
            new_story["id"] = new_story["slug"] = "new-science-story"
            new_story["brief"] = "Researchers published a new, independently sourced science result."
            new_story["sources"] = [{
                "publisher": "Example Science",
                "title": "New science result",
                "url": "https://example.com/unverified",
            }]
            new_story["image"] = None
            valid_seed = {key: value for key, value in new_story.items() if key != "levels"}
            invalid_seed = {**valid_seed, "slug": "Not a valid slug"}
            prose = _plain_adaptation(new_story)
            segmentation = _segmentation(new_story)
            translations = _translations(new_story)
            call = Mock(side_effect=[
                {
                    "stories": [invalid_seed],
                    PROVENANCE_ERRORS_KEY: ["https://example.com/unverified"],
                },
                {"stories": [valid_seed]},
                {"adaptations": [prose]},
                {"adaptations": [segmentation]},
                {"translations": [translations]},
            ])
            with patch.dict(os.environ, {"OPENAI_MODEL": "test-model"}), patch(
                "src.generate_issue._call_openai",
                call,
            ):
                result = generate(root, "2024-01-26", 1)
            self.assertEqual(call.call_count, 5)
            self.assertIn("expected lowercase ASCII kebab-case", call.call_args_list[1].args[2])
            self.assertEqual(result["stories"][-1]["id"], "new-science-story")

    def test_segmentation_cannot_change_frozen_hebrew(self) -> None:
        story = copy.deepcopy(read_json(ROOT / "content" / "2024-01-26.json")["stories"][1])
        prose = _plain_adaptation(story)
        segmentation = _segmentation(story)
        self.assertEqual(_segmentation_preservation_errors([prose], [segmentation]), [])
        segmentation["levels"]["alef"]["paragraphs"][0][0]["text"] += "ש"
        errors = _segmentation_preservation_errors([prose], [segmentation])
        self.assertTrue(any("changed frozen Hebrew" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
