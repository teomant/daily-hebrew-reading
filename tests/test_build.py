from __future__ import annotations

import copy
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

from src.build_site import build, build_day, build_home, render_units
from src.common import ROOT, load_level_config, load_locales, load_site_config, read_json, units_text


class LinkCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        attribute = "href" if tag in {"a", "link"} else "src" if tag in {"img", "script"} else None
        if attribute and values.get(attribute):
            self.links.append(values[attribute] or "")


class BuildTests(unittest.TestCase):
    def test_missing_separator_units_get_readable_spaces(self) -> None:
        units = [
            {"text": "בנק", "type": "word", "translations": {}},
            {"text": "ישראל", "type": "properNoun", "translations": {}},
            {"text": "מוריד", "type": "word", "translations": {}},
            {"text": "ל", "type": "separator", "translations": {}},
            {"text": "3.25%", "type": "word", "translations": {}},
        ]
        self.assertEqual(units_text(units), "בנק ישראל מוריד ל3.25%")
        self.assertIn("</button> <button", render_units(units, interactive=True))

    def test_whitespace_inside_clickable_units_is_rendered_between_buttons(self) -> None:
        units = [
            {"text": "ירושלים ", "type": "properNoun", "translations": {"ru": "Иерусалим"}},
            {"text": "מצילה ", "type": "word", "translations": {"ru": "спасает"}},
            {"text": "אוכל", "type": "word", "translations": {"ru": "еду"}},
        ]
        rendered = render_units(units, interactive=True)
        self.assertIn(">ירושלים</button> <button", rendered)
        self.assertIn(">מצילה</button> <button", rendered)
        self.assertNotIn(">ירושלים </button>", rendered)

    def test_home_does_not_keep_image_column_without_an_image(self) -> None:
        issue = copy.deepcopy(read_json(ROOT / "content" / "2024-01-26.json"))
        issue["stories"][0]["image"] = None
        rendered = build_home(issue, read_json(ROOT / "content" / "index.json"), load_site_config(), load_level_config(), load_locales())
        self.assertIn('class="home-hero"', rendered)
        self.assertNotIn('class="home-hero has-image"', rendered)

    def test_home_lists_the_complete_issue(self) -> None:
        issue = copy.deepcopy(read_json(ROOT / "content" / "2024-01-26.json"))
        template = issue["stories"][1]
        for index in range(3):
            story = copy.deepcopy(template)
            story["id"] = story["slug"] = f"extra-story-{index}"
            issue["stories"].append(story)
        rendered = build_home(issue, read_json(ROOT / "content" / "index.json"), load_site_config(), load_level_config(), load_locales())
        self.assertIn('data-story-index="5"', rendered)

    def test_everyday_story_is_disclosed_as_ai_generated(self) -> None:
        issue = read_json(ROOT / "content" / "2024-01-26.json")
        rendered = build_home(issue, read_json(ROOT / "content" / "index.json"), load_site_config(), load_level_config(), load_locales())
        self.assertIn("ПОЛНОСТЬЮ СОЗДАНО ИИ", rendered)

    def test_dialog_has_its_own_type_and_ai_disclosure(self) -> None:
        issue = copy.deepcopy(read_json(ROOT / "content" / "2024-01-26.json"))
        issue["stories"][1]["type"] = "dialog"
        rendered = build_home(issue, read_json(ROOT / "content" / "index.json"), load_site_config(), load_level_config(), load_locales())
        self.assertIn("DIALOG", rendered)
        self.assertIn("ПОЛНОСТЬЮ СОЗДАНО ИИ", rendered)

    def test_old_issue_builds_when_a_new_level_becomes_default(self) -> None:
        issue = read_json(ROOT / "content" / "2024-01-26.json")
        site = {**load_site_config(), "defaultReadingLevel": "gimel"}
        levels = [*load_level_config(), {"id": "gimel", "label": "ג", "name": "Gimel", "approximateCefr": "B1", "learnerWordsPerMinute": 75}]
        rendered = build_day(issue, site, levels, load_locales())
        self.assertIn('data-level="alef"', rendered)
        self.assertNotIn('data-level="gimel"', rendered)

    def test_build_creates_every_page_with_project_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = build(ROOT, Path(temporary) / "site")
            expected = [
                "index.html",
                "archive/index.html",
                "2024-01-26/index.html",
                "2024-01-26/ingenuity-final-flight/index.html",
                "2024-01-26/late-furniture-delivery/index.html",
                "2024-01-26/baird-first-television-demo/index.html",
                "assets/styles.css",
                "assets/app.js",
            ]
            for relative in expected:
                self.assertTrue((output / relative).is_file(), relative)
            home = (output / "index.html").read_text(encoding="utf-8")
            article = (output / expected[3]).read_text(encoding="utf-8")
            self.assertIn('/daily-hebrew-reading/assets/styles.css', home)
            self.assertIn('id="interface-locale"', home)
            self.assertIn('class="lexeme"', article)
            self.assertNotIn("OPENAI_API_KEY", home + article)

            prefix = "/daily-hebrew-reading/"
            for html_path in output.rglob("*.html"):
                collector = LinkCollector()
                collector.feed(html_path.read_text(encoding="utf-8"))
                for link in collector.links:
                    parsed = urlparse(link)
                    if parsed.scheme or parsed.netloc or not parsed.path.startswith(prefix):
                        continue
                    relative = parsed.path.removeprefix(prefix)
                    target = output / relative
                    if parsed.path.endswith("/"):
                        target /= "index.html"
                    self.assertTrue(target.is_file(), f"broken internal link in {html_path}: {link}")


if __name__ == "__main__":
    unittest.main()
