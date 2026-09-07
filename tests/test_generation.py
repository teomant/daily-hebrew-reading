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
    _adaptation_batch_schema,
    _call_openai,
    _compact_story_record,
    _duplicate_findings,
    _existing_exclusions,
    _forbidden_story_records,
    _generated_planning_request,
    _remove_redundant_sources,
    _recent_history,
    _recent_issue_context,
    _safe_log_text,
    _seed_batch_schema,
    _seed_errors,
    _sourced_discovery_request,
    _transactional_write,
    _updated_history,
    generate,
)
from src.validation import validate_repository


class GenerationTests(unittest.TestCase):
    def test_adaptation_schema_allows_one_line_per_dialog_turn(self) -> None:
        schema = _adaptation_batch_schema(
            ["family-dialog"],
            [{"id": "alef"}],
            ["ru", "en"],
            ["ru", "en"],
        )
        paragraphs = (
            schema["properties"]["adaptations"]["items"]
            ["properties"]["levels"]["properties"]["alef"]
            ["properties"]["paragraphs"]
        )
        self.assertEqual(paragraphs["minItems"], 4)
        self.assertEqual(paragraphs["maxItems"], 12)

        prompt = (ROOT / "prompts" / "adaptation.md").read_text(encoding="utf-8")
        self.assertIn("8–12 short turns", prompt)
        self.assertIn("exactly one complete speaker turn", prompt)
        self.assertIn("separate line", prompt)
        self.assertIn("Never place two speaker labels", prompt)

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
                        "sources": [{"url": f"https://example.com/{issue_date}"}],
                    }]
                }
                (content_dir / f"{issue_date}.json").write_text(json.dumps(payload), encoding="utf-8")
            context = _recent_issue_context(content_dir, date.fromisoformat("2026-09-05"), 3)
        self.assertEqual([item["date"] for item in context], ["2026-09-04", "2026-09-02"])
        self.assertEqual(context[0]["stories"][0]["sourceUrls"], ["https://example.com/2026-09-04"])
        self.assertEqual(context[0]["stories"][0]["type"], "current")

    def test_phase_prompts_receive_only_relevant_forbidden_records(self) -> None:
        existing = read_json(ROOT / "content" / "2026-09-06.json")
        exclusions = _existing_exclusions(existing)
        self.assertEqual(set(exclusions), {"stories"})
        self.assertEqual(set(exclusions["stories"][0]), {"id", "type", "brief", "sourceUrls"})
        previous = [{
            "date": "2026-09-05",
            "stories": [{
                "id": "previous-story",
                "type": "current",
                "brief": "A previous story that must not be repeated.",
                "sourceUrls": ["https://example.com/previous-story"],
            }, {
                "id": "previous-dialog",
                "type": "dialog",
                "brief": "Two relatives decide when to leave home.",
                "sourceUrls": [],
            }],
        }]
        sourced = _forbidden_story_records(exclusions, previous, {"current", "history"})
        generated = _forbidden_story_records(exclusions, previous, {"everyday", "dialog"})
        self.assertTrue(all(record["type"] in {"current", "history"} for record in sourced))
        self.assertTrue(all(record["type"] in {"everyday", "dialog"} for record in generated))

        request = _sourced_discovery_request("2026-09-06", 4, 2, sourced, [])
        self.assertIn("FORBIDDEN SOURCED STORIES", request)
        self.assertIn("A previous story that must not be repeated.", request)
        self.assertIn("https://example.com/previous-story", request)
        self.assertIn("NOVELTY CONTRACT", request)
        self.assertIn("same central entity or subject and the same underlying event", request)
        self.assertNotIn("previous-dialog", request)
        self.assertNotIn("Configured reading levels", request)
        self.assertNotIn("Required translation locales", request)

    def test_sourced_discovery_searches_broadly_and_retries_with_web_search(self) -> None:
        request = _sourced_discovery_request(
            "2026-09-07",
            4,
            2,
            [],
            [],
            ["duplicate source URL: https://example.com/old"],
        )
        self.assertIn("begin from the target date", request)
        self.assertIn("Do not formulate searches from forbidden", request)
        self.assertIn("Search more candidates than requested", request)
        self.assertIn("whole country", request)
        self.assertIn("do not default to Jerusalem", request)
        self.assertIn("HISTORY does not need a connection to the target date", request)
        self.assertIn("continue searching for another candidate", request)
        self.assertIn("continuing the search", request)

    def test_generated_planning_forbids_exact_recent_scenarios(self) -> None:
        request = _generated_planning_request(
            "2026-09-07",
            6,
            3,
            3,
            False,
            [],
            [{
                "date": "2026-09-06",
                "storyId": "pharmacy-prescription-delay",
                "domain": "pharmacy",
                "scenario": "pharmacy_prescription_not_ready",
            }],
            [],
        )
        self.assertIn("only EVERYDAY and DIALOG", request)
        self.assertIn("Do not use web search", request)
        self.assertIn("<forbidden_scenario_records>", request)
        self.assertIn('"scenario": "pharmacy_prescription_not_ready"', request)
        self.assertIn("An identical `scenario` value is always a duplicate", request)
        self.assertIn("Changing its identifier, names, setting details, wording, or story type", request)
        self.assertNotIn("canonical HTTPS", request)
        self.assertNotIn("Configured reading levels", request)

    def test_new_issue_rejects_a_previous_day_story_before_adaptation(self) -> None:
        site = read_json(ROOT / "config" / "site.json")
        levels = read_json(ROOT / "config" / "reading-levels.json")["levels"]
        previous_story = read_json(ROOT / "content" / "2024-01-26.json")["stories"][0]
        seed = {
            key: copy.deepcopy(value)
            for key, value in previous_story.items()
            if key != "levels"
        }
        seed["id"] = seed["slug"] = "ingenuity-flight-story-with-new-date"
        recent_stories = [{
            "id": previous_story["id"],
            "brief": previous_story["brief"],
            "sourceUrls": [source["url"] for source in previous_story["sources"]],
        }]
        errors = _seed_errors(
            [seed],
            "2026-09-07",
            [level["id"] for level in levels],
            site["translationLocales"],
            site,
            levels,
            None,
            1,
            1,
            recent_stories,
        )
        self.assertTrue(any("duplicate source URL" in error for error in errors), errors)
        self.assertTrue(any("near-duplicate story briefs" in error for error in errors), errors)

    def test_append_seed_schema_only_accepts_everyday_or_dialog(self) -> None:
        schema = _seed_batch_schema(3, 3, [], ["ru", "en"], ["ru", "en"], ["everyday", "dialog"])
        story_types = schema["properties"]["stories"]["items"]["properties"]["type"]["enum"]
        self.assertEqual(story_types, ["everyday", "dialog"])

    def test_recent_scenario_history_is_compact_for_prompt_context(self) -> None:
        history = {
            "items": [{
                "date": "2026-09-05",
                "storyId": "late-delivery",
                "domain": "delivery",
                "scenario": "late_delivery",
                "lexicalThemes": ["waiting", "complaints"],
                "targetVocabulary": ["עדיין לא", "מתי בערך"],
            }],
        }
        recent = _recent_history(history, date.fromisoformat("2026-09-06"), 30)
        self.assertEqual(
            recent,
            [{
                "date": "2026-09-05",
                "storyId": "late-delivery",
                "domain": "delivery",
                "scenario": "late_delivery",
            }],
        )

    def test_python_rejects_an_exact_recent_scenario(self) -> None:
        story = copy.deepcopy(read_json(ROOT / "content" / "2024-01-26.json")["stories"][1])
        story.pop("levels")
        story["id"] = story["slug"] = "different-story-id"
        story["brief"] = "A different-looking brief uses the same recent scenario identifier."
        scenario = story["everydayMeta"]["scenario"]
        errors, indexes = _duplicate_findings(
            [story],
            None,
            [{"storyId": "old-story", "scenario": scenario}],
        )
        self.assertEqual(indexes, {0})
        self.assertIn(f"duplicate generated scenario: {scenario}", errors)
        self.assertEqual(_compact_story_record(story)["scenario"], scenario)

    def test_new_issue_does_not_require_fixed_story_type_counts(self) -> None:
        site = read_json(ROOT / "config" / "site.json")
        levels = read_json(ROOT / "config" / "reading-levels.json")["levels"]
        briefs = [
            "A city adds a late bus on a busy route.",
            "A supermarket changes how reusable bags are sold.",
            "A neighborhood library opens a tool-lending shelf.",
            "A cafe introduces advance pickup for breakfast orders.",
            "A local pool extends its evening opening hours.",
            "A clinic introduces appointment reminders by text message.",
            "A railway station changes its passenger pickup area.",
            "A market offers a collection point for used batteries.",
            "A community center opens registration for cooking classes.",
            "A bus company adds clearer signs at a central stop.",
        ]
        seeds = [
            {
                "id": f"story-{index}",
                "slug": f"story-{index}",
                "type": "current",
                "category": "city",
                "brief": brief,
                "everydayMeta": None,
                "sources": [],
                "image": None,
            }
            for index, brief in enumerate(briefs)
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
        self.assertEqual(errors, [])

    def test_duplicate_findings_identify_only_rejected_slots(self) -> None:
        stories = [
            {
                "id": "unique-bus-change",
                "slug": "unique-bus-change",
                "brief": "A bus route adds a new evening stop near a neighborhood clinic.",
                "sources": [],
            },
            {
                "id": "unique-bus-change-details",
                "slug": "unique-bus-change-details",
                "brief": "A bus route adds a new evening stop near a neighborhood clinic.",
                "sources": [],
            },
            {
                "id": "different-cafe-order",
                "slug": "different-cafe-order",
                "brief": "A customer changes a cafe pickup time before leaving work.",
                "sources": [],
            },
        ]
        errors, indexes = _duplicate_findings(stories, None)
        self.assertTrue(errors)
        self.assertEqual(indexes, {1})

    def test_new_issue_accepts_the_target_everyday_and_dialog_mix(self) -> None:
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

    def test_full_issue_append_allows_any_generated_story_type_mix(self) -> None:
        site = read_json(ROOT / "config" / "site.json")
        levels = read_json(ROOT / "config" / "reading-levels.json")["levels"]
        existing = read_json(ROOT / "content" / "2026-09-06.json")
        template = next(story for story in existing["stories"] if story["type"] == "everyday")
        briefs = [
            "Two siblings decide who will collect a package before the shop closes.",
            "A neighborhood opens a shaded place to wait for the bus.",
            "An old bakery sign is restored and returned to its original street.",
        ]
        story_types = ["dialog", "everyday", "dialog"]
        seeds = []
        for index, (brief, story_type) in enumerate(zip(briefs, story_types, strict=True)):
            seed = {key: copy.deepcopy(value) for key, value in template.items() if key != "levels"}
            seed["id"] = seed["slug"] = f"append-story-{index}"
            seed["type"] = story_type
            seed["brief"] = brief
            seed["everydayMeta"]["scenario"] = f"append_scenario_{index}"
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

        seeds[1]["type"] = "current"
        seeds[1]["everydayMeta"] = None
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
        self.assertTrue(any("append stories must be EVERYDAY or DIALOG" in error for error in errors), errors)

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
        with (
            patch.dict(sys.modules, {"openai": SimpleNamespace(OpenAI=openai)}),
            patch("src.generate_issue._log_prompt") as log_prompt,
        ):
            self.assertEqual(_call_openai("test-model", "instructions", "request", {}), output)
        log_prompt.assert_called_once_with("OpenAI request", "instructions", "request")

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

    def test_new_issue_runs_three_isolated_prompt_stages(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for directory in ("config", "i18n", "prompts", "content"):
                shutil.copytree(ROOT / directory, root / directory)
            sample = read_json(root / "content" / "2024-01-26.json")
            templates = {story["type"]: story for story in sample["stories"]}
            sourced_specs = [
                ("coastal-evening-trains", "current", "A rail operator adds late evening trains on a coastal route after commuters request more options."),
                ("northern-weekend-market", "current", "A northern town opens a weekend produce market where residents can buy directly from nearby farms."),
                ("clinic-lab-hours", "current", "A health clinic extends walk-in laboratory hours so working patients can arrive after their shifts."),
                ("reusable-produce-crates", "current", "Several supermarkets introduce reusable produce crates and explain the deposit return process to shoppers."),
                ("postal-bus-route-history", "history", "An early postal bus route connected small communities and carried both letters and passengers."),
                ("public-beach-showers-history", "history", "A coastal municipality installed its first public beach showers as bathing facilities became more organized."),
            ]
            generated_specs = [
                ("neighbor-borrows-drill", "everyday", "A neighbor borrows a drill, agrees on a return time, and brings it back after finishing a shelf."),
                ("family-chooses-picnic-food", "dialog", "Two relatives choose simple picnic food, clarify what is already at home, and divide the shopping."),
                ("tailor-shortens-trousers", "everyday", "A customer asks a tailor to shorten trousers, checks the pickup day, and confirms the price."),
                ("friends-change-walk-time", "dialog", "Two friends move their evening walk because one finishes work late and agree where to meet."),
                ("office-mug-mixup", "everyday", "Two colleagues discover they took similar mugs, compare them, and exchange them with a laugh."),
                ("parents-plan-library-stop", "dialog", "Two parents coordinate a library return, check closing time, and decide who will go with the children."),
            ]

            def make_seed(story_id: str, story_type: str, brief: str, index: int) -> tuple[dict, dict]:
                template_type = story_type if story_type in templates else "everyday"
                template = copy.deepcopy(templates[template_type])
                seed = {key: value for key, value in template.items() if key != "levels"}
                seed["id"] = seed["slug"] = story_id
                seed["type"] = story_type
                seed["brief"] = brief
                seed["sources"] = []
                seed["image"] = None
                if story_type in {"current", "history"}:
                    seed["everydayMeta"] = None
                else:
                    seed["everydayMeta"]["scenario"] = f"isolated_stage_scenario_{index}"
                return seed, {"id": story_id, "levels": template["levels"]}

            pairs = [
                make_seed(story_id, story_type, brief, index)
                for index, (story_id, story_type, brief) in enumerate([*sourced_specs, *generated_specs])
            ]
            sourced = [seed for seed, _ in pairs[:len(sourced_specs)]]
            generated = [seed for seed, _ in pairs[len(sourced_specs):]]
            adaptations = [adaptation for _, adaptation in pairs]
            duplicate_history = copy.deepcopy(sourced[-2])
            call = Mock(side_effect=[
                {"stories": [*sourced[:-1], duplicate_history]},
                {"stories": [sourced[-1]]},
                {"stories": generated},
                {"adaptations": adaptations},
            ])
            with (
                patch.dict(os.environ, {"OPENAI_MODEL": "test-model"}),
                patch("src.generate_issue.ADAPTATION_BATCH_SIZE", 12),
                patch("src.generate_issue._call_openai", call),
            ):
                result = generate(root, "2026-09-10", 3)

            self.assertEqual(call.call_count, 4)
            self.assertEqual(call.call_args_list[0].kwargs["phase"], "Sourced discovery attempt 1/2")
            self.assertTrue(call.call_args_list[0].kwargs["use_web_search"])
            self.assertIn("# Sourced discovery instructions", call.call_args_list[0].args[1])
            self.assertNotIn("# Everyday-story instructions", call.call_args_list[0].args[1])
            self.assertEqual(call.call_args_list[1].kwargs["phase"], "Sourced discovery attempt 2/2")
            self.assertTrue(call.call_args_list[1].kwargs["use_web_search"])
            self.assertIn("RETRY FEEDBACK", call.call_args_list[1].args[2])
            self.assertIn("ALREADY SELECTED SOURCED STORIES", call.call_args_list[1].args[2])
            self.assertEqual(call.call_args_list[2].kwargs["phase"], "Generated planning attempt 1/3")
            self.assertFalse(call.call_args_list[2].kwargs["use_web_search"])
            self.assertNotIn("# Sourced discovery instructions", call.call_args_list[2].args[1])
            self.assertIn("# Everyday-story instructions", call.call_args_list[2].args[1])
            self.assertEqual(call.call_args_list[3].kwargs["phase"], "Adaptation batch 1/1, attempt 1/2")
            self.assertIn("# Adaptation and annotation instructions", call.call_args_list[3].args[1])
            self.assertEqual(len(result["stories"]), 12)

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

    def test_duplicate_seed_is_replaced_with_an_ai_story(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for directory in ("config", "i18n", "prompts", "content"):
                shutil.copytree(ROOT / directory, root / directory)
            original = read_json(root / "content" / "2024-01-26.json")
            duplicate_seed = {
                key: copy.deepcopy(value)
                for key, value in original["stories"][1].items()
                if key != "levels"
            }
            replacement = copy.deepcopy(original["stories"][1])
            replacement["id"] = replacement["slug"] = "changed-family-shopping-list"
            replacement["brief"] = (
                "Two relatives compare the shopping list, remove an unnecessary item, "
                "and agree who will visit the supermarket."
            )
            replacement["type"] = "dialog"
            replacement["everydayMeta"]["domain"] = "family"
            replacement["everydayMeta"]["scenario"] = "revise_shared_shopping_list"
            replacement_seed = {
                key: copy.deepcopy(value)
                for key, value in replacement.items()
                if key != "levels"
            }
            adaptation = {"id": replacement["id"], "levels": replacement["levels"]}
            call = Mock(side_effect=[
                {"stories": [duplicate_seed]},
                {"stories": [replacement_seed]},
                {"adaptations": [adaptation]},
            ])
            with patch.dict(os.environ, {"OPENAI_MODEL": "test-model"}), patch(
                "src.generate_issue._call_openai",
                call,
            ):
                result = generate(root, "2024-01-26", 1)
            self.assertEqual(call.call_count, 3)
            self.assertIn("RETRY FEEDBACK", call.call_args_list[1].args[2])
            self.assertIn("Generate unrelated replacements", call.call_args_list[1].args[2])
            replacement_schema = call.call_args_list[1].args[3]
            replacement_types = replacement_schema["properties"]["stories"]["items"]["properties"]["type"]["enum"]
            self.assertEqual(replacement_types, ["everyday", "dialog"])
            self.assertFalse(call.call_args_list[1].kwargs["use_web_search"])
            self.assertEqual(result["stories"][-1]["id"], "changed-family-shopping-list")

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
            self.assertEqual(call.call_args_list[0].kwargs["phase"], "Generated planning attempt 1/3")
            self.assertFalse(call.call_args_list[0].kwargs["use_web_search"])
            self.assertEqual(call.call_args_list[1].kwargs["phase"], "Adaptation batch 1/1, attempt 1/2")
            self.assertEqual(call.call_args_list[2].kwargs["phase"], "Adaptation batch 1/1, attempt 2/2")
            generated_instructions = call.call_args_list[0].args[1]
            adaptation_instructions = call.call_args_list[1].args[1]
            self.assertNotIn("# Sourced discovery instructions", generated_instructions)
            self.assertIn("# Everyday-story instructions", generated_instructions)
            self.assertIn("# Dialogue instructions", generated_instructions)
            self.assertNotIn("# Adaptation and annotation instructions", generated_instructions)
            self.assertIn("# Adaptation and annotation instructions", adaptation_instructions)
            self.assertNotIn("# Sourced discovery instructions", adaptation_instructions)
            self.assertIn("one to three Hebrew words", adaptation_instructions)
            self.assertIn("Never put a complete sentence", adaptation_instructions)
            self.assertIn("never emit forms such as `ב העיר`", adaptation_instructions)
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

    def test_invalid_generated_plan_is_retried_before_adaptation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for directory in ("config", "i18n", "prompts", "content"):
                shutil.copytree(ROOT / directory, root / directory)
            original = read_json(root / "content" / "2024-01-26.json")
            new_story = copy.deepcopy(original["stories"][1])
            new_story["id"] = new_story["slug"] = "new-cafe-order"
            new_story["brief"] = "A customer changes a cafe order before the staff starts preparing it."
            new_story["everydayMeta"]["domain"] = "cafe"
            new_story["everydayMeta"]["scenario"] = "change_order_before_preparation"
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
            self.assertIn("expected lowercase ASCII kebab-case", call.call_args_list[1].args[2])
            self.assertEqual(result["stories"][-1]["id"], "new-cafe-order")


if __name__ == "__main__":
    unittest.main()
