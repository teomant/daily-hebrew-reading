from __future__ import annotations

import copy
import json
import os
import re
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date, timedelta
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from src.common import ROOT, load_level_config, load_locales, load_site_config, prioritize_practice_pages, read_json
from src.build_site import build, build_article, build_archive
from src.generate_issue import _adapt_story, _generate_verbs_page, _ordered_issue_stories, generate
from src.validation import validate_issue, validate_repository
from src.verbs import daily_verbs, load_verbs, uses_target_verb, verb_batch_index, verb_seed, verbs_page


def units(text):
    return [{"text": word, "type": "separator" if word in '.!?' else "word",
             "translations": {"en": "test" if word not in '.!?' else "", "ru": "тест" if word not in '.!?' else ""}}
            for word in re.findall(r'[א-ת]+|[.!?]', text)]


def level_text(verb):
    return {"title": units("רגע קטן"), "teaser": units("זה רגע קטן."),
            "paragraphs": [units(f"אני רוצה {verb}. זה טוב.")]}


class VerbTests(unittest.TestCase):
    def setUp(self):
        self.site = load_site_config()
        self.levels = load_level_config()
        self.locales = self.site["translationLocales"]
        self.day = "2026-10-29"

    def page(self):
        items = daily_verbs(ROOT, self.day)
        stories = [{"levels": {level["id"]: level_text(item["verb"]) for level in self.levels}} for item in items]
        return verbs_page(items, stories, self.day, [level["id"] for level in self.levels], self.locales)

    def issue(self, page):
        return {"schemaVersion": 1, "date": self.day, "availableLevels": [level["id"] for level in self.levels],
                "translationLocales": self.locales, "stories": [page]}

    def test_five_days_cover_all_fifty_once_and_repeat(self):
        self.assertEqual(verb_batch_index("0001-01-01"), 0)
        for first in (date(2026, 12, 29), date(2024, 2, 27)):
            batches = [daily_verbs(ROOT, (first + timedelta(days=i)).isoformat()) for i in range(6)]
            self.assertEqual(batches[0], batches[5])
            self.assertEqual(sorted(item["rank"] for batch in batches[:5] for item in batch), list(range(1, 51)))
            self.assertTrue(all(len(batch) == 10 for batch in batches))
        self.assertEqual(len({item["verb"] for item in load_verbs(ROOT)}), 50)
        self.assertEqual(load_verbs(ROOT)[0]["verb"], "לבטל")
        self.assertEqual(load_verbs(ROOT)[-1]["verb"], "ללמוד")

    def test_catalog_rejects_missing_duplicate_or_reordered_entries(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'config').mkdir()
            data = read_json(ROOT / 'config/common-verbs.json')
            for change in ('missing', 'duplicate', 'rank'):
                broken = copy.deepcopy(data)
                if change == 'missing':
                    broken['verbs'].pop()
                elif change == 'duplicate':
                    broken['verbs'][1]['verb'] = broken['verbs'][0]['verb']
                else:
                    broken['verbs'][0]['rank'] = 2
                (root / 'config/common-verbs.json').write_text(json.dumps(broken))
                with self.assertRaises(ValueError):
                    load_verbs(root)

    def test_target_is_a_body_word_not_a_substring(self):
        self.assertTrue(uses_target_verb(units('אני רוצה ללכת.'), 'ללכת'))
        self.assertFalse(uses_target_verb(units('אני רוצה וללכת.'), 'ללכת'))
        self.assertTrue(uses_target_verb([{'text': 'לָלֶכֶת'}], 'ללכת'))

    def test_page_validation_requires_all_ten_targets_and_body_translations(self):
        page = self.page()
        self.assertEqual(validate_issue(self.issue(page), self.site, self.levels), [])
        for defect in ('missing', 'duplicate', 'target', 'translation', 'metadata'):
            broken = copy.deepcopy(page)
            if defect == 'missing':
                broken['levels']['alef']['paragraphs'].pop()
            elif defect == 'duplicate':
                broken['verbItems'][1] = broken['verbItems'][0]
            elif defect == 'target':
                broken['levels']['alef']['paragraphs'][0] = units('אני כאן. זה טוב.')
            elif defect == 'metadata':
                broken['verbItems'][0] = None
            else:
                for unit in broken['levels']['alef']['paragraphs'][0]:
                    unit['translations'] = {'ru': '', 'en': ''}
            self.assertTrue(validate_issue(self.issue(broken), self.site, self.levels), defect)
        self.assertIsNone(verbs_page(daily_verbs(ROOT, self.day), [], self.day, ['alef'], self.locales))

    def test_retry_only_failed_level_and_never_accept_missing_target(self):
        item = daily_verbs(ROOT, self.day)[0]
        seed = verb_seed(item, self.day)
        requested = []
        def respond(model, instructions, request, schema, **kwargs):
            self.assertFalse(kwargs['use_web_search'])
            ids = schema['properties']['adaptations']['items']['properties']['levels']['required']
            requested.append(ids)
            levels = {key: level_text(item['verb']) for key in ids}
            if len(requested) == 1:
                levels['bet']['paragraphs'] = [units('אני כאן. זה טוב.')]
            return {'adaptations': [{'id': seed['id'], 'levels': levels, 'coveredStoryBeatIds': {key: [] for key in ids}}]}
        with patch.dict(os.environ, OPENAI_MODEL='test'), patch('src.generate_issue._call_openai', side_effect=respond), redirect_stdout(StringIO()):
            result = _adapt_story(seed, self.day, self.levels, self.locales, self.site, self.locales, '', 'VERBS test')
        self.assertEqual(requested, [['alef', 'alefPlus', 'bet'], ['bet']])
        self.assertNotIn('_targetVerb', result)
        self.assertTrue(uses_target_verb(result['levels']['bet']['paragraphs'][0], item['verb']))

    def test_item_failures_omit_only_the_page_without_extra_calls(self):
        def fail(*args, **kwargs):
            raise RuntimeError('offline simulated request failure')
        with patch.dict(os.environ, OPENAI_MODEL='test'), patch('src.generate_issue._call_openai', side_effect=fail) as call, redirect_stdout(StringIO()):
            result = _generate_verbs_page(ROOT, self.day, self.levels, self.locales, self.site, self.locales, '')
        self.assertIsNone(result)
        self.assertEqual(call.call_count, 30)

    def test_annotation_repair_cannot_hide_missing_body_translations_behind_title(self):
        item = daily_verbs(ROOT, self.day)[0]
        seed = verb_seed(item, self.day)
        body = f"אני רוצה {item['verb']}. זה טוב."
        original = level_text(item['verb'])
        # Enough translated title units to mask an untranslated body in an aggregate check.
        original['title'] = units(' '.join(['רגע'] * 40))
        original['paragraphs'] = [[{'text': body, 'type': 'expression', 'translations': {'en': 'test', 'ru': 'тест'}}]]
        repair_units = units(body)
        for unit in repair_units:
            unit['translations'] = {'en': '', 'ru': ''}
        responses = [
            {'adaptations': [{'id': seed['id'], 'levels': {'alef': original}, 'coveredStoryBeatIds': {'alef': []}}]},
            {'repairs': [{'id': 'alef/paragraphs/0', 'units': repair_units}]},
        ]
        with patch.dict(os.environ, OPENAI_MODEL='test'), patch('src.generate_issue._call_openai', side_effect=responses) as call, redirect_stdout(StringIO()) as log:
            story = _adapt_story(seed, self.day, self.levels[:1], self.locales, self.site, self.locales, '', 'VERBS test')
        self.assertEqual(story['levels']['alef']['paragraphs'], original['paragraphs'])
        self.assertEqual(call.call_count, 2)
        self.assertIn('repair rejected', log.getvalue())

    def test_missing_target_exhausts_only_that_item_and_keeps_other_articles(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for directory in ('config', 'prompts'):
                shutil.copytree(ROOT / directory, root / directory)
            (root / 'content').mkdir()
            site = {**self.site, 'defaultIssueStoryCount': 2, 'minimumIssueStoryCount': 1, 'maximumIssueStoryCount': 2}
            (root / 'config/site.json').write_text(json.dumps(site))
            item = daily_verbs(ROOT, self.day)[0]
            short = verb_seed(item, self.day)
            short = {key: value for key, value in short.items() if not key.startswith('_')}
            short.update(id='tea-for-a-neighbor', slug='tea-for-a-neighbor',
                         brief='A neighbor brings fresh mint to a shared kitchen and the cook adds it to a pot of tea.')
            short['everydayMeta']['domain'] = 'food_cooking'
            calls = []

            def respond(model, instructions, request, schema, **kwargs):
                phase = kwargs['phase']
                calls.append(phase)
                if phase.startswith('SHORTS planning'):
                    return {'stories': [short]}
                if phase.startswith('VERBS item'):
                    result = self.verb_response(model, instructions, request, schema, **kwargs)
                    if phase.startswith(f"VERBS item {item['rank']}/"):
                        for value in result['adaptations'][0]['levels'].values():
                            value['paragraphs'] = [units('אני כאן. זה טוב.')]
                    return result
                self.assertTrue(phase.startswith('Adaptation batch'), phase)
                return {'adaptations': [{'id': short['id'],
                                        'levels': {level['id']: level_text(item['verb']) for level in self.levels},
                                        'coveredStoryBeatIds': {level['id']: [] for level in self.levels}}]}

            with (patch.dict(os.environ, OPENAI_MODEL='test'), patch('src.generate_issue.CURRENT_TARGET', 0),
                  patch('src.generate_issue.HISTORY_TARGET', 0), patch('src.generate_issue.EVERYDAY_TARGET', 0),
                  patch('src.generate_issue.DIALOG_TARGET', 0), patch('src.generate_issue.SHORTS_TARGET', 1),
                  patch('src.generate_issue._call_openai', side_effect=respond), redirect_stdout(StringIO()) as log):
                issue = generate(root, self.day, 0)
            self.assertEqual([story['type'] for story in issue['stories']], ['shorts'])
            self.assertEqual(sum(phase.startswith('VERBS item') for phase in calls), 12)
            self.assertIn('only 9/10 items passed core checks', log.getvalue())
            self.assertEqual(len(issue['stories'][0]['shortItems']), 1)

    def test_page_rendering_and_order(self):
        page = self.page()
        issue = self.issue(page)
        html = build_article(issue, 0, self.site, self.levels, load_locales())
        self.assertEqual(html.count('class="short-item"'), 10)
        self.assertIn('class="hebrew-article shorts-list"', html)
        self.assertIn('ПОЛНОСТЬЮ СОЗДАНО ИИ', html)
        archive = build_archive({'dates': [{'date': self.day, 'storyCount': 1, 'readingMinutes': 1}]}, {self.day: issue}, self.site, self.levels, load_locales())
        self.assertIn('data-type-count="verbs"', archive)
        stories = [{'type': kind, 'id': str(index)} for index, kind in enumerate(['current', 'everyday', 'shorts', 'verbs', 'history', 'dialog', 'everyday'])]
        self.assertEqual([s['id'] for s in prioritize_practice_pages(stories)], ['3', '2', '0', '1', '4', '5', '6'])
        self.assertEqual([s['id'] for s in _ordered_issue_stories(stories)], ['3', '2', '1', '6', '5', '0', '4'])

    def test_new_issue_includes_verbs_and_append_does_not_regenerate_it(self):
        # A small offline pipeline covers integration without sourced research.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for directory in ('config', 'prompts', 'i18n', 'static'):
                shutil.copytree(ROOT / directory, root / directory)
            (root / 'content').mkdir()
            site = {**self.site, 'defaultIssueStoryCount': 2, 'minimumIssueStoryCount': 1, 'maximumIssueStoryCount': 2}
            (root / 'config/site.json').write_text(json.dumps(site))
            with (patch.dict(os.environ, OPENAI_MODEL='test'), patch('src.generate_issue.CURRENT_TARGET', 0),
                  patch('src.generate_issue.HISTORY_TARGET', 0), patch('src.generate_issue.EVERYDAY_TARGET', 0),
                  patch('src.generate_issue.DIALOG_TARGET', 0),
                  patch('src.generate_issue._call_openai', side_effect=self.verb_response),
                  redirect_stdout(StringIO())):
                # SHORTS planning is allowed to fail; VERBS still produces the issue.
                issue = generate(root, self.day, 0)
            self.assertEqual([story['type'] for story in issue['stories']], ['verbs'])
            self.assertEqual(validate_repository(root), [])
            output = build(root, root / 'output')
            self.assertTrue((output / self.day / issue['stories'][0]['slug'] / 'index.html').exists())
            with patch.dict(os.environ, OPENAI_MODEL='test'), patch('src.generate_issue._generate_verbs_page') as verbs, patch('src.generate_issue._call_openai', side_effect=RuntimeError('offline')), redirect_stdout(StringIO()):
                with self.assertRaises(RuntimeError):
                    generate(root, self.day, 1)
            verbs.assert_not_called()

    def verb_response(self, model, instructions, request, schema, **kwargs):
        self.assertFalse(kwargs['use_web_search'])
        if not kwargs['phase'].startswith('VERBS item'):
            raise RuntimeError('offline planning failure')
        contract = schema['properties']['adaptations']['items']['properties']
        story_id = contract['id']['enum'][0]
        rank = int(story_id.split('-')[1])
        verb = load_verbs(ROOT)[rank - 1]['verb']
        ids = contract['levels']['required']
        return {'adaptations': [{'id': story_id, 'levels': {key: level_text(verb) for key in ids},
                                'coveredStoryBeatIds': {key: [] for key in ids}}]}
