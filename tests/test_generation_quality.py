from __future__ import annotations

import copy
import json
import os
import unittest
from unittest.mock import Mock, patch

from src.common import ROOT, read_json, units_text
from src.generate_issue import (_adapt_story, _adaptation_content_errors, _compact_story_record,
    _existing_exclusions, _recent_history, _recent_issue_context, _shorts_page, _updated_history)
from src.generation_quality import affected_groups, apply_repairs, segmentation_errors
from src.validation import validate_issue
from tests.test_generation import adaptation_payload, lexical_unit, valid_dialog_levels
from datetime import date
import tempfile
from pathlib import Path


def words(text: str) -> list[dict]:
    import re
    return [lexical_unit(part, "separator" if part in '.!?…:;' else "word")
            for part in re.findall(r"[^\s.!?…:;]+|[.!?…:;]", text)]


class QualityTests(unittest.TestCase):
    def setUp(self):
        self.site = read_json(ROOT / 'config/site.json')
        self.levels = read_json(ROOT / 'config/reading-levels.json')['levels']
        self.story = copy.deepcopy(next(s for s in read_json(ROOT / 'content/2024-01-26.json')['stories'] if s['type'] == 'everyday'))
        self.story['levels'] = adaptation_payload(self.story['id'], self.story['levels'])['levels']
        self.seed = {k: v for k, v in self.story.items() if k != 'levels'}

    def adapt(self, call):
        with patch.dict(os.environ, {'OPENAI_MODEL': 'test-model'}), patch('src.generate_issue._call_openai', call):
            return _adapt_story(self.seed, '2099-01-01', self.levels, ['ru', 'en'], self.site, ['ru', 'en'], 'instructions', 'Adaptation test')

    def test_sentence_spans_include_separate_punctuation_and_dialog_labels(self):
        for units in ([lexical_unit('אני הולך הביתה.')],
                      [lexical_unit('אני הולך הביתה'), lexical_unit('.', 'separator')],
                      [lexical_unit('דנה', 'properNoun'), lexical_unit(':', 'separator'), lexical_unit('אני בבית. הוא בחוץ.')],
                      [lexical_unit('"אני בבית."')]):
            self.assertTrue(segmentation_errors(units, dialog=True), units)
        self.assertEqual(segmentation_errors(words('אני בבית. הוא בחוץ.')), [])
        self.assertEqual(segmentation_errors([lexical_unit('תודה רבה!')]), [])
        self.assertEqual(segmentation_errors([lexical_unit('שלום.')]), [])
        self.assertEqual(segmentation_errors([lexical_unit('תל אביב', 'properNoun'), lexical_unit('.', 'separator')]), [])
        self.assertTrue(segmentation_errors([lexical_unit('תל אביב. באר שבע.', 'properNoun')]))
        self.assertTrue(segmentation_errors([lexical_unit('אחד שניים שלושה ארבעה חמישה', 'properNoun')]))

    def test_repair_is_atomic_and_preserves_exact_text(self):
        self.story['levels']['alef']['teaser'] = [lexical_unit('אני הולך הביתה.')]
        groups = affected_groups(self.story)
        before = copy.deepcopy(self.story)
        repair = {'repairs': [{'id': groups[0]['id'], 'units': words(groups[0]['text'])}]}
        repaired, errors = apply_repairs(self.story, groups, repair, ['ru', 'en'])
        self.assertEqual(errors, [])
        self.assertEqual(units_text(repaired['levels']['alef']['teaser']), 'אני הולך הביתה.')
        self.assertEqual(self.story, before)
        repair['repairs'][0]['units'] = words('אני הולך לחנות.')
        self.assertIsNone(apply_repairs(self.story, groups, repair, ['ru', 'en'])[0])
        repair['repairs'] *= 2
        self.assertIsNone(apply_repairs(self.story, groups, repair, ['ru', 'en'])[0])

    def test_level_retry_retains_successes_and_requests_only_failed_level(self):
        first = adaptation_payload(self.seed['id'], self.story['levels'])
        for group in [first['levels']['alef']['title'], first['levels']['alef']['teaser'], *first['levels']['alef']['paragraphs']]:
            for unit in group:
                unit['translations']['ru'] = ''
        second = adaptation_payload(self.seed['id'], {'alef': self.story['levels']['alef']})
        call = Mock(side_effect=[{'adaptations': [first]}, {'adaptations': [second]}])
        result = self.adapt(call)
        self.assertIsNotNone(result)
        self.assertEqual(result['levels']['bet'], first['levels']['bet'])
        level_schema = call.call_args_list[1].args[3]['properties']['adaptations']['items']['properties']['levels']
        self.assertEqual(level_schema['required'], ['alef'])
        self.assertNotIn('"id": "bet"', call.call_args_list[1].args[2])
        self.assertEqual(call.call_count, 2)

    def test_missing_level_is_retried_without_replacing_successes(self):
        first = adaptation_payload(self.seed['id'], {key: val for key, val in self.story['levels'].items() if key != 'alef'})
        second = adaptation_payload(self.seed['id'], {'alef': self.story['levels']['alef']})
        self.assertIsNotNone(self.adapt(Mock(side_effect=[{'adaptations': [first]}, {'adaptations': [second]}])))
        # Unexpected levels must not overwrite retained output.
        second['levels']['bet'] = copy.deepcopy(self.story['levels']['bet'])
        self.assertIsNone(self.adapt(Mock(side_effect=[{'adaptations': [first]}, {'adaptations': [second]}])))

    def test_annotation_repair_only_sends_failed_groups_and_has_one_attempt(self):
        first = adaptation_payload(self.seed['id'], self.story['levels'])
        first['levels']['alef']['teaser'] = [lexical_unit('אני הולך הביתה.')]
        repair = {'repairs': [{'id': 'alef/teaser', 'units': words('אני הולך הביתה.')}]}
        call = Mock(side_effect=[{'adaptations': [first]}, repair])
        result = self.adapt(call)
        self.assertIsNotNone(result)
        self.assertEqual(result['levels']['bet'], first['levels']['bet'])
        request = json.loads(call.call_args_list[1].args[2])
        self.assertEqual([g['id'] for g in request['groups']], ['alef/teaser'])
        self.assertEqual(set(request['contextByLevel']), {'alef'})
        self.assertFalse(call.call_args_list[1].kwargs['use_web_search'])
        for failed in ({'repairs': []}, RuntimeError('unavailable')):
            call = Mock(side_effect=[{'adaptations': [first]}, failed])
            retained = self.adapt(call)
            self.assertIsNotNone(retained)
            self.assertEqual(retained["levels"], first["levels"])
            self.assertEqual(call.call_count, 2)

    def test_unknown_speakers_and_labeled_narration_are_rejected(self):
        seed = {'id': 'dialog-test', 'type': 'dialog', 'everydayMeta': {'dialogSpeakers': ['נועה', 'דני']}}
        adaptation = adaptation_payload(seed['id'], valid_dialog_levels())
        adaptation['levels']['alef']['paragraphs'][0] = words('נועה: נועה קיבלה פתק.')
        errors = _adaptation_content_errors([seed], [adaptation], self.levels)
        self.assertTrue(any('narrated DIALOG turn 1' in e for e in errors))
        adaptation['levels']['alef']['paragraphs'][0] = words('יעל: אני כאן.')
        self.assertTrue(any('planned names' in e for e in _adaptation_content_errors([seed], [adaptation], self.levels)))

    def test_usable_dialogue_is_retained_after_bounded_style_retries(self):
        self.seed['type'] = 'dialog'
        self.seed['everydayMeta']['dialogSpeakers'] = ['נועה', 'דני']
        adaptation = adaptation_payload(self.seed['id'], valid_dialog_levels())
        for level in adaptation['levels'].values():
            level['paragraphs'][0] = words('נועה: נועה קיבלה פתק.')
        call = Mock(return_value={'adaptations': [adaptation]})
        retained = self.adapt(call)
        self.assertIsNotNone(retained)
        self.assertEqual(retained["levels"], adaptation["levels"])
        self.assertEqual(call.call_count, 3)

    def test_style_warning_does_not_discard_successful_annotation_repair(self):
        self.seed['type'] = 'dialog'
        self.seed['everydayMeta']['dialogSpeakers'] = ['נועה', 'דני']
        adaptation = adaptation_payload(self.seed['id'], valid_dialog_levels())
        for level in adaptation['levels'].values():
            level['paragraphs'][0] = words('נועה: נועה קיבלה פתק.')
        adaptation['levels']['alef']['teaser'] = [lexical_unit('אני הולך הביתה.')]
        repair = {'repairs': [{'id': 'alef/teaser', 'units': words('אני הולך הביתה.')}]}
        call = Mock(side_effect=[{'adaptations': [adaptation]} for _ in range(3)] + [repair])
        retained = self.adapt(call)
        self.assertIsNotNone(retained)
        self.assertGreater(len(retained['levels']['alef']['teaser']), 1)
        self.assertEqual(units_text(retained['levels']['alef']['paragraphs'][0]), 'נועה: נועה קיבלה פתק.')

    def test_patterns_and_short_briefs_survive_history_and_append_context(self):
        pattern = dict(goal='Share a task', relationship='Two siblings', interaction='Cooperate', outcome='Finish together')
        self.story['everydayMeta']['storyPattern'] = pattern
        page = _shorts_page([self.story], '2099-01-01', [l['id'] for l in self.levels], ['ru', 'en'])
        history = _updated_history({'items': []}, [page], '2099-01-01')
        self.assertEqual(history['items'][0]['storyPattern'], pattern)
        self.assertEqual(_recent_history(history, date(2099, 1, 2), 7)[0]['brief'], self.story['brief'])
        record = _existing_exclusions({'stories': [page]})['stories'][0]
        self.assertEqual(record['storyPattern'], pattern)
        self.assertEqual(record['brief'], self.story['brief'])
        self.assertEqual(_compact_story_record(self.story)['storyPattern'], pattern)
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, '2099-01-01.json').write_text(json.dumps({'stories': [page]}))
            self.assertEqual(_recent_issue_context(Path(folder), date(2099, 1, 2), 7)[0]['stories'][0]['storyPattern'], pattern)
        self.assertEqual(affected_groups(page), [])
        issue = {'schemaVersion': 1, 'date': '2099-01-01', 'availableLevels': list(self.story['levels']), 'translationLocales': ['ru', 'en'], 'stories': [self.story]}
        self.assertEqual(validate_issue(issue, self.site, self.levels), [])
        self.story['everydayMeta']['storyPattern']['goal'] = ''
        self.assertTrue(any('storyPattern' in e for e in validate_issue(issue, self.site, self.levels)))
        self.story['everydayMeta'].pop('storyPattern')
        self.assertEqual(validate_issue(issue, self.site, self.levels), [])
