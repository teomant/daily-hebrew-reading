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

    def test_sourced_story_requires_real_source(self) -> None:
        issue = copy.deepcopy(read_json(ROOT / "content" / "2024-01-26.json"))
        issue["stories"][0]["sources"] = []
        errors = validate_issue(issue, load_site_config(), load_level_config())
        self.assertTrue(any("require at least one source" in error for error in errors), errors)

    def test_equivalent_source_urls_are_duplicates(self) -> None:
        for suffix in ("/", "?utm_source=duplicate-test"):
            with self.subTest(suffix=suffix):
                issue = copy.deepcopy(read_json(ROOT / "content" / "2024-01-26.json"))
                first_url = issue["stories"][0]["sources"][0]["url"]
                issue["stories"][2]["sources"][0]["url"] = first_url + suffix
                errors = validate_issue(issue, load_site_config(), load_level_config())
                self.assertTrue(any("duplicate source URL" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
