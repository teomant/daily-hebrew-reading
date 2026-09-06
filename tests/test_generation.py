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

from src.common import ROOT, read_json
from src.generate_issue import (
    PROVENANCE_ERRORS_KEY,
    _call_openai,
    _remove_redundant_sources,
    _recent_issue_context,
    _safe_log_text,
    _seed_errors,
    _transactional_write,
    _updated_history,
    generate,
)
from src.validation import validate_repository


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

    def test_new_issue_requires_three_everyday_and_three_dialog_stories(self) -> None:
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
        self.assertTrue(any("requires exactly 3 EVERYDAY" in error for error in errors), errors)
        self.assertTrue(any("requires exactly 3 DIALOG" in error for error in errors), errors)

    def test_new_issue_accepts_the_required_everyday_and_dialog_mix(self) -> None:
        site = read_json(ROOT / "config" / "site.json")
        levels = read_json(ROOT / "config" / "reading-levels.json")["levels"]
        story_types = ["current"] * 4 + ["everyday"] * 3 + ["dialog"] * 3 + ["history"] * 2
        briefs = [
            "A city adds a late bus on a busy route.",
            "A supermarket changes how reusable bags are sold.",
            "A neighborhood library opens a tool-lending shelf.",
            "A cafe introduces advance pickup for breakfast orders.",
            "A parent replaces a missing item from a school bag.",
            "A tenant arranges a convenient time for a repair visit.",
            "A customer returns shoes that do not fit comfortably.",
            "Two relatives decide what groceries to buy for dinner.",
            "A couple agrees how to divide errands before guests arrive.",
            "A child and parent clarify where to meet after school.",
            "An old train station becomes a community building.",
            "A familiar market street gets its modern name.",
        ]
        seeds = []
        for index, (story_type, brief) in enumerate(zip(story_types, briefs, strict=True)):
            generated = story_type in {"everyday", "dialog"}
            seeds.append(
                {
                    "id": f"story-{index}",
                    "slug": f"story-{index}",
                    "type": story_type,
                    "category": "everyday" if generated else "history" if story_type == "history" else "city",
                    "brief": brief,
                    "everydayMeta": {
                        "domain": f"domain-{index}",
                        "scenario": f"scenario_{index}",
                        "lexicalThemes": ["plans"],
                        "targetVocabulary": ["להחליט"],
                    } if generated else None,
                    "sources": [],
                    "image": None,
                }
            )
        errors = _seed_errors(
            seeds,
            "2026-09-07",
            [level["id"] for level in levels],
            site["translationLocales"],
            site,
            levels,
            None,
            10,
            13,
        )
        self.assertEqual(errors, [])

    def test_full_issue_append_fills_missing_dialogs_first(self) -> None:
        site = read_json(ROOT / "config" / "site.json")
        levels = read_json(ROOT / "config" / "reading-levels.json")["levels"]
        existing = read_json(ROOT / "content" / "2026-09-06.json")
        template = next(story for story in existing["stories"] if story["type"] == "everyday")
        briefs = [
            "Two siblings decide who will collect a package before the shop closes.",
            "Parents agree what to cook after discovering an ingredient is missing.",
            "A grandparent and child arrange where to meet after an afternoon class.",
        ]
        seeds = []
        for index, brief in enumerate(briefs):
            seed = {key: copy.deepcopy(value) for key, value in template.items() if key != "levels"}
            seed["id"] = seed["slug"] = f"family-dialog-{index}"
            seed["type"] = "dialog"
            seed["brief"] = brief
            seed["everydayMeta"]["scenario"] = f"family_dialog_{index}"
            seeds.append(seed)
        errors = _seed_errors(
            seeds,
            existing["date"],
            existing["availableLevels"],
            existing["translationLocales"],
            site,
            levels,
            existing,
            3,
            3,
        )
        self.assertEqual(errors, [])

        seeds[0]["type"] = "everyday"
        errors = _seed_errors(
            seeds,
            existing["date"],
            existing["availableLevels"],
            existing["translationLocales"],
            site,
            levels,
            existing,
            3,
            3,
        )
        self.assertTrue(any("append requires 3 DIALOG" in error for error in errors), errors)

    def test_dialog_is_recorded_in_scenario_history(self) -> None:
        story = {
            "id": "family-dinner-dialog",
            "type": "dialog",
            "everydayMeta": {
                "domain": "family",
                "scenario": "choose_dinner",
                "lexicalThemes": ["plans"],
                "targetVocabulary": ["מה בא לך"],
            },
        }
        history = _updated_history({"schemaVersion": 1, "items": []}, [story], "2026-09-07")
        self.assertEqual(history["items"][0]["storyId"], "family-dinner-dialog")

    def test_append_rejects_a_rephrased_existing_topic(self) -> None:
        site = read_json(ROOT / "config" / "site.json")
        levels = read_json(ROOT / "config" / "reading-levels.json")["levels"]
        existing = copy.deepcopy(read_json(ROOT / "content" / "2024-01-26.json"))
        existing["stories"][0]["brief"] = (
            "Several desalination plants shut down after murky seawater raised turbidity, "
            "while authorities asked residents to reduce irrigation and save water at home."
        )
        seed = copy.deepcopy(existing["stories"][0])
        seed["id"] = seed["slug"] = "save-water-after-plant-shutdowns"
        seed["brief"] = (
            "Authorities asked residents to save water at home and reduce irrigation after "
            "murky seawater raised turbidity and shut down several desalination plants."
        )
        seed["sources"] = []
        seed["image"] = None
        seed.pop("levels")
        errors = _seed_errors(
            [seed],
            existing["date"],
            existing["availableLevels"],
            existing["translationLocales"],
            site,
            levels,
            existing,
            1,
            1,
        )
        self.assertTrue(any("near-duplicate story" in error for error in errors), errors)

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
            for level in new_story["levels"].values():
                level["title"].append({"text": "", "type": "separator", "translations": {"ru": "", "en": ""}})
            adaptation = {"id": new_story["id"], "levels": new_story["levels"]}
            with patch.dict(os.environ, {"OPENAI_MODEL": "test-model"}), patch(
                "src.generate_issue._call_openai",
                side_effect=[{"stories": [seed]}, {"adaptations": [adaptation]}],
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
            adaptation = {"id": new_story["id"], "levels": new_story["levels"]}
            call = Mock(side_effect=[
                {"stories": [seed]},
                RuntimeError("OpenAI generation failed (APIConnectionError)"),
                {"adaptations": [adaptation]},
            ])
            with patch.dict(os.environ, {"OPENAI_MODEL": "test-model"}), patch(
                "src.generate_issue._call_openai",
                call,
            ):
                result = generate(root, "2024-01-26", 1)
            self.assertEqual(call.call_count, 3)
            self.assertEqual(call.call_args_list[0].kwargs["phase"], "Research attempt 1/3")
            self.assertEqual(call.call_args_list[1].kwargs["phase"], "Adaptation batch 1/1, attempt 1/2")
            self.assertEqual(call.call_args_list[2].kwargs["phase"], "Adaptation batch 1/1, attempt 2/2")
            self.assertEqual(result["stories"][-1]["id"], "changed-train-platform")

    def test_adaptation_accepts_empty_translation_above_coverage_threshold(self) -> None:
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
            adaptation = {"id": new_story["id"], "levels": levels}
            call = Mock(side_effect=[
                {"stories": [seed]},
                {"adaptations": [copy.deepcopy(adaptation)]},
                {"adaptations": [copy.deepcopy(adaptation)]},
            ])
            with patch.dict(os.environ, {"OPENAI_MODEL": "test-model"}), patch(
                "src.generate_issue._call_openai",
                call,
            ):
                result = generate(root, "2024-01-26", 1)
            self.assertEqual(call.call_count, 2)
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
            adaptation = {"id": new_story["id"], "levels": new_story["levels"]}
            call = Mock(side_effect=[
                {
                    "stories": [invalid_seed],
                    PROVENANCE_ERRORS_KEY: ["https://example.com/unverified"],
                },
                {"stories": [valid_seed]},
                {"adaptations": [adaptation]},
            ])
            with patch.dict(os.environ, {"OPENAI_MODEL": "test-model"}), patch(
                "src.generate_issue._call_openai",
                call,
            ):
                result = generate(root, "2024-01-26", 1)
            self.assertEqual(call.call_count, 3)
            self.assertIn("expected lowercase ASCII kebab-case", call.call_args_list[1].args[2])
            self.assertEqual(result["stories"][-1]["id"], "new-science-story")


if __name__ == "__main__":
    unittest.main()
