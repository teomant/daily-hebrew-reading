from __future__ import annotations

import copy
import unittest

from src.common import ROOT, load_level_config, load_site_config, read_json
from src.validation import validate_issue, validate_repository


class ValidationTests(unittest.TestCase):
    def test_sample_repository_is_valid(self) -> None:
        self.assertEqual(validate_repository(ROOT), [])

    def test_missing_translation_is_rejected(self) -> None:
        issue = copy.deepcopy(read_json(ROOT / "content" / "2024-01-26.json"))
        del issue["stories"][0]["levels"]["alef"]["title"][0]["translations"]["en"]
        errors = validate_issue(issue, load_site_config(), load_level_config())
        self.assertTrue(any("missing ['en']" in error for error in errors), errors)

    def test_empty_translation_is_allowed(self) -> None:
        issue = copy.deepcopy(read_json(ROOT / "content" / "2024-01-26.json"))
        issue["stories"][0]["levels"]["alef"]["title"][0]["translations"]["en"] = ""
        errors = validate_issue(issue, load_site_config(), load_level_config())
        self.assertEqual(errors, [])

    def test_translation_coverage_below_seventy_five_percent_is_rejected(self) -> None:
        issue = copy.deepcopy(read_json(ROOT / "content" / "2024-01-26.json"))
        level = issue["stories"][0]["levels"]["alef"]
        for units in [level["title"], level["teaser"], *level["paragraphs"]]:
            for unit in units:
                if unit["type"] != "separator":
                    unit["translations"]["en"] = ""
        errors = validate_issue(issue, load_site_config(), load_level_config())
        self.assertTrue(any("expected at least 75%" in error for error in errors), errors)

    def test_sourced_story_may_have_no_source(self) -> None:
        issue = copy.deepcopy(read_json(ROOT / "content" / "2024-01-26.json"))
        issue["stories"][0]["sources"] = []
        issue["stories"][0]["image"] = None
        errors = validate_issue(issue, load_site_config(), load_level_config())
        self.assertEqual(errors, [])

    def test_dialog_uses_scenario_metadata_and_has_no_sources(self) -> None:
        issue = copy.deepcopy(read_json(ROOT / "content" / "2024-01-26.json"))
        story = issue["stories"][1]
        story["type"] = "dialog"
        errors = validate_issue(issue, load_site_config(), load_level_config())
        self.assertEqual(errors, [])

        story["sources"] = copy.deepcopy(issue["stories"][0]["sources"])
        errors = validate_issue(issue, load_site_config(), load_level_config())
        self.assertTrue(any("DIALOG stories cannot have sources" in error for error in errors), errors)

    def test_source_url_with_control_characters_is_rejected(self) -> None:
        for unsafe_suffix in ("\n::error::spoof", "\u0085spoof", "\u2028spoof", "\u202espoof"):
            with self.subTest(unsafe_suffix=repr(unsafe_suffix)):
                issue = copy.deepcopy(read_json(ROOT / "content" / "2024-01-26.json"))
                issue["stories"][0]["sources"][0]["url"] += unsafe_suffix
                errors = validate_issue(issue, load_site_config(), load_level_config())
                self.assertTrue(any("expected a valid HTTPS URL" in error for error in errors), errors)

    def test_equivalent_source_urls_are_duplicates(self) -> None:
        for suffix in ("/", "?utm_source=duplicate-test"):
            with self.subTest(suffix=suffix):
                issue = copy.deepcopy(read_json(ROOT / "content" / "2024-01-26.json"))
                first_url = issue["stories"][0]["sources"][0]["url"]
                issue["stories"][2]["sources"][0]["url"] = first_url + suffix
                errors = validate_issue(issue, load_site_config(), load_level_config())
                self.assertTrue(any("duplicate source URL" in error for error in errors), errors)

    def test_rephrased_topic_is_rejected_with_a_different_source(self) -> None:
        issue = copy.deepcopy(read_json(ROOT / "content" / "2024-01-26.json"))
        issue["stories"][0]["brief"] = (
            "Jerusalem plans a street-by-street infrastructure revamp of Mahane Yehuda market "
            "so businesses can keep operating during deliveries, repairs, and construction."
        )
        duplicate = copy.deepcopy(issue["stories"][0])
        duplicate["id"] = duplicate["slug"] = "mahane-yehuda-renovation"
        duplicate["brief"] = (
            "Businesses at Jerusalem's Mahane Yehuda market can keep operating while a major "
            "infrastructure renovation proceeds street by street around deliveries and repairs."
        )
        duplicate["sources"][0]["url"] = "https://example.com/a-different-report"
        duplicate["image"] = None
        issue["stories"].append(duplicate)
        errors = validate_issue(issue, load_site_config(), load_level_config())
        self.assertTrue(any("near-duplicate story topic" in error for error in errors), errors)

    def test_hebrew_internal_brief_is_rejected(self) -> None:
        issue = copy.deepcopy(read_json(ROOT / "content" / "2024-01-26.json"))
        issue["stories"][0]["brief"] = "זהו תקציר פנימי בעברית שלא ניתן להשוות לתקצירים באנגלית."
        errors = validate_issue(issue, load_site_config(), load_level_config())
        self.assertTrue(any("internal brief must be written in English" in error for error in errors), errors)

    def test_near_duplicate_story_slug_is_rejected(self) -> None:
        issue = copy.deepcopy(read_json(ROOT / "content" / "2024-01-26.json"))
        original = issue["stories"][0]
        original["id"] = original["slug"] = "whatsapp-school-contact-rules"
        duplicate = copy.deepcopy(issue["stories"][1])
        duplicate["id"] = duplicate["slug"] = "whatsapp-teacher-contact-rules"
        issue["stories"].append(duplicate)
        errors = validate_issue(issue, load_site_config(), load_level_config())
        self.assertTrue(any("near-duplicate story ID" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
