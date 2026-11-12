from __future__ import annotations

import copy
import json
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from src.common import ROOT, load_level_config, load_site_config, read_json, write_json
from src.editions import build_index, edition_issue, to_editions, topic_records
from src.generate_issue import _adapt_editions, _shorts_page, _updated_history, generate
from src.migrate_editions import migrate
from src.validation import validate_issue, validate_repository
from src.verbs import daily_verbs, verbs_page
from src.build_site import build


def content(title="בבנק"):
    def units(words):
        return [{"text": word, "type": "word", "translations": {"en": "test", "ru": "тест"}}
                for word in words.split()]
    return {"title": units(title), "teaser": units("אני בבנק."),
            "paragraphs": [units("אני בבנק."), units("אני רוצה חשבון.")]}


class EditionTests(unittest.TestCase):
    def setUp(self):
        self.levels = load_level_config()
        self.site = load_site_config()
        self.legacy = read_json(ROOT / "tests/fixtures/legacy-issue.json")
        self.seed = {
            "id": "opening-a-bank-account", "slug": "opening-a-bank-account",
            "type": "everyday", "category": "consumer",
            "brief": "An adult visits a bank to open an account and asks which documents to bring.",
            "sources": [], "image": None,
            "everydayMeta": {"domain": "banking_credit", "scenario": "opening_bank_account",
                "lexicalThemes": ["banking"], "targetVocabulary": ["חשבון"], "dialogSpeakers": [],
                "storyPattern": {"goal": "open account", "relationship": "customer and clerk",
                                 "interaction": "ask about documents", "outcome": "prepare identification"}},
        }

    def root(self, path):
        for directory in ("config", "i18n", "prompts", "static"):
            shutil.copytree(ROOT / directory, path / directory)
        write_json(path / "content/2024-01-26.json", self.legacy)
        write_json(path / "content/index.json", build_index({self.legacy["date"]: self.legacy}, self.levels))
        write_json(path / "content/everyday-history.json",
                   _updated_history({"schemaVersion": 1, "items": []}, self.legacy["stories"], self.legacy["date"]))
        return path

    def response(self, model, instructions, request, schema, **kwargs):
        if "stories" in schema["properties"]:
            return {"stories": [copy.deepcopy(self.seed)]}
        contract = schema["properties"]["adaptations"]["items"]
        ids = contract["properties"]["levels"]["required"]
        self.assertEqual(len(ids), 1)
        self.assertFalse(kwargs["use_web_search"])
        level_id = ids[0]
        scenario = {"brief": self.seed["brief"] + f" This is the {level_id} account-opening situation.",
                    "everydayMeta": copy.deepcopy(self.seed["everydayMeta"])}
        scenario["everydayMeta"]["scenario"] += "_" + level_id
        return {"adaptations": [{"id": self.seed["id"], "levels": {level_id: content()},
                                 "coveredStoryBeatIds": {level_id: []}, "scenario": scenario}]}

    def test_migration_is_lossless_dry_run_and_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.root(Path(directory))
            before = (root / "content/2024-01-26.json").read_bytes()
            self.assertEqual(migrate(root)["changedIssues"], 1)
            self.assertEqual(before, (root / "content/2024-01-26.json").read_bytes())
            migrate(root, write=True)
            migrated = read_json(root / "content/2024-01-26.json")
            for level_id in self.legacy["availableLevels"]:
                for original, article in zip(self.legacy["stories"], migrated["editions"][level_id]["stories"]):
                    self.assertEqual(article["content"], original["levels"][level_id])
                    self.assertEqual({key: value for key, value in article.items() if key not in {"content", "topicId"}},
                                     {key: value for key, value in original.items() if key != "levels"})
            self.assertEqual(migrate(root, write=True)["changedFiles"], 0)
            self.assertEqual(validate_repository(root), [])

    def test_editions_accept_distinct_fiction_but_not_inconsistent_shared_research(self):
        issue = to_editions(self.legacy)
        issue["editions"]["bet"]["stories"][1]["brief"] = "A family checks a furniture delivery and chooses another arrival time."
        self.assertEqual(validate_issue(issue, self.site, self.levels), [])
        issue["editions"]["bet"]["stories"][0]["brief"] = "An entirely different news event with a different set of facts."
        self.assertTrue(any("shared research" in error for error in validate_issue(issue, self.site, self.levels)))

    def test_stale_legacy_index_reports_error_for_edition_content(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.root(Path(directory))
            migrate(root, write=True)
            write_json(root / "content/index.json", {"schemaVersion": 1, "dates": [
                {"date": self.legacy["date"], "storyCount": 3, "readingMinutes": 1}]})
            self.assertTrue(any("schema 2 is required" in error for error in validate_repository(root)))

    def test_one_level_per_request_and_actual_scenario_metadata(self):
        with patch.dict(os.environ, OPENAI_MODEL="test"), patch("src.generate_issue._call_openai", side_effect=self.response) as call, redirect_stdout(StringIO()):
            result = _adapt_editions(self.seed, "2026-11-12", self.levels, ["en", "ru"], self.site,
                                     ["en", "ru"], "test", "Writing")
        self.assertEqual(call.call_count, 3)
        self.assertEqual(set(result["levels"]), {"alef", "alefPlus", "bet"})
        for level_id, story in result["_editionStories"].items():
            self.assertIn(level_id, story["brief"])
            self.assertTrue(story["everydayMeta"]["scenario"].endswith(level_id))
            self.assertNotIn("_independentEdition", story)

    def test_failed_level_does_not_discard_successful_articles(self):
        def response(*args, **kwargs):
            if "edition bet" in kwargs["phase"]:
                raise RuntimeError("offline simulated failure")
            return self.response(*args, **kwargs)
        with patch.dict(os.environ, OPENAI_MODEL="test"), patch("src.generate_issue._call_openai", side_effect=response), redirect_stdout(StringIO()):
            result = _adapt_editions(self.seed, "2026-11-12", self.levels, ["en", "ru"], self.site,
                                     ["en", "ru"], "test", "Writing")
        self.assertEqual(set(result["levels"]), {"alef", "alefPlus"})

    def test_append_keeps_existing_editions_and_writes_per_edition_history(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.root(Path(directory))
            migrate(root, write=True)
            before = read_json(root / "content/2024-01-26.json")
            with patch.dict(os.environ, OPENAI_MODEL="test"), patch("src.generate_issue._call_openai", side_effect=self.response), redirect_stdout(StringIO()):
                result = generate(root, "2024-01-26", 1)
            self.assertEqual(result["schemaVersion"], 2)
            for level_id, edition in result["editions"].items():
                by_id = {article["id"]: article for article in edition["stories"]}
                for original in before["editions"][level_id]["stories"]:
                    self.assertEqual(by_id[original["id"]], original)
                self.assertIn(level_id, by_id[self.seed["id"]]["brief"])
            history = read_json(root / "content/everyday-history.json")
            self.assertEqual({item.get("edition") for item in history["items"] if item["storyId"] == self.seed["id"]},
                             {"alef", "alefPlus", "bet"})
            self.assertEqual(validate_repository(root), [])

    def test_grouped_practice_keeps_each_editions_successful_items(self):
        pieces = [{**self.seed, "levels": {"alef": {**content(), "paragraphs": [content()["paragraphs"][0]]}}}]
        shorts = _shorts_page(pieces, "2026-11-12", ["alef", "bet"], ["en", "ru"])
        self.assertEqual(set(shorts["levels"]), {"alef"})
        self.assertEqual(len(shorts["levels"]["alef"]["paragraphs"]), 1)
        ten = [{"levels": {"alef": content(), **({"bet": content()} if index < 9 else {})}} for index in range(10)]
        page = verbs_page(daily_verbs(ROOT, "2026-11-12"), ten, "2026-11-12", ["alef", "bet"], ["en", "ru"])
        self.assertEqual(set(page["levels"]), {"alef"})

    def test_routes_and_payloads_stay_in_the_selected_edition(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.root(Path(directory))
            migrate(root, write=True)
            output = build(root, root / "output", "/project/")
            for level_id, route in (("alef", "alef"), ("alefPlus", "alef-plus"), ("bet", "bet")):
                path = output / route / "2024-01-26/late-furniture-delivery/index.html"
                page = path.read_text()
                runtime = json.loads(page.split('<script id="dhr-data" type="application/json">')[1].split('</script>')[0])
                self.assertEqual(runtime["payload"]["readingLevel"], level_id)
                self.assertNotIn('data-level=', page)
                self.assertNotIn('class="edition-control"', page)
                self.assertIn('class="edition-badge"', page)
                for story in runtime["payload"]["issue"]["stories"]:
                    self.assertEqual(list(story["levels"]), [level_id])
                self.assertTrue(all(url.startswith(f"/project/{route}/") for url in runtime["payload"]["randomArticles"]))
                self.assertIn(f'href="/project/{route}/archive/"', page)
                self.assertTrue((output / route / "archive/index.html").exists())
            legacy = (output / "2024-01-26/late-furniture-delivery/index.html").read_text()
            self.assertIn('"page":"redirect"', legacy)
            self.assertIn('/project/alef-plus/2024-01-26/late-furniture-delivery/', legacy)


if __name__ == "__main__":
    unittest.main()
