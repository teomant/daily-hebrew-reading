from __future__ import annotations

import json
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from src.generation_usage import record_usage, usage_record, usage_run
from src.generate_issue import _call_openai


def response_data(**overrides):
    data = {'model': 'gpt-6-luna', 'service_tier': 'default', 'usage': {
        'input_tokens': 1000, 'input_tokens_details': {'cached_tokens': 400},
        'output_tokens': 200, 'output_tokens_details': {'reasoning_tokens': 50}},
        'output': [{'type': 'web_search_call'}, {'type': 'web_search_call'}, {'type': 'message'}]}
    data.update(overrides)
    return data


class UsageTests(unittest.TestCase):
    def test_prices_cache_and_search_without_double_counting_reasoning(self):
        record = usage_record('gpt-6-luna', 'adapt', response_data())
        self.assertAlmostEqual(record['estimated_usd'], .020164)
        self.assertEqual(record['web_search_calls'], 2)
        self.assertEqual(record['reasoning_tokens'], 50)
        other = response_data()
        other['usage']['output_tokens_details']['reasoning_tokens'] = 150
        self.assertEqual(usage_record('gpt-6-luna', 'adapt', other)['estimated_usd'], record['estimated_usd'])

    def test_long_context_and_unknown_pricing(self):
        data = response_data(output=[])
        data['usage']['input_tokens'] = 272001
        self.assertAlmostEqual(usage_record('gpt-6-luna', 'x', data)['estimated_usd'], .0544782)
        for change in ({'model': 'another-model'}, {'service_tier': 'priority'}, {'usage': None}):
            self.assertIsNone(usage_record('gpt-6-luna', 'x', response_data(**change))['estimated_usd'])
        self.assertIsNone(usage_record('gpt-6-luna', 'x', None)['input_tokens'])
        data['usage']['input_tokens_details'] = {}
        self.assertIsNone(usage_record('gpt-6-luna', 'x', data)['estimated_usd'])

    def test_summary_on_exception_and_run_isolation(self):
        log = Mock()
        with self.assertRaises(ValueError), usage_run(log):
            record_usage('gpt-6-luna', 'ok', response_data(), log)
            record_usage('gpt-6-luna', 'missing', None, log)
            raise ValueError('test')
        total = json.loads(log.call_args.args[0].split(': ', 1)[1])
        self.assertEqual(total['requests'], 2)
        self.assertEqual(total['input_tokens_observed'], 1000)
        self.assertEqual(total['input_tokens_unknown_requests'], 1)
        self.assertEqual(total['unpriced_requests'], 1)
        self.assertFalse(total['usage_complete'])
        with usage_run(log):
            pass
        self.assertEqual(json.loads(log.call_args.args[0].split(': ', 1)[1])['requests'], 0)

    def test_malformed_response_still_logs_usage_once(self):
        response = SimpleNamespace(output_text='not JSON', model_dump=lambda: response_data())
        client = Mock()
        client.return_value.responses.create.return_value = response
        log = Mock()
        with patch.dict(sys.modules, {'openai': SimpleNamespace(OpenAI=client)}), patch('src.generate_issue._log', log), patch('src.generate_issue._log_prompt'), usage_run(log):
            with self.assertRaises(RuntimeError):
                _call_openai('gpt-6-luna', 'secret-free instructions', 'request', {}, use_web_search=False)
        records = [call.args[0] for call in log.call_args_list if call.args[0].startswith('API usage:')]
        self.assertEqual(len(records), 1)
        self.assertEqual(json.loads(records[0].split(': ', 1)[1])['input_tokens'], 1000)
        self.assertNotIn('not JSON', records[0])
        self.assertEqual(client.return_value.responses.create.call_args.kwargs['service_tier'], 'default')

    def test_request_failure_logs_unknown_usage(self):
        client = Mock()
        client.return_value.responses.create.side_effect = RuntimeError('private error details')
        log = Mock()
        with patch.dict(sys.modules, {'openai': SimpleNamespace(OpenAI=client)}), patch('src.generate_issue._log', log), patch('src.generate_issue._log_prompt'):
            with self.assertRaises(RuntimeError):
                _call_openai('gpt-6-luna', 'instructions', 'request', {})
        records = [c.args[0] for c in log.call_args_list if c.args[0].startswith('API usage:')]
        self.assertIsNone(json.loads(records[0].split(': ', 1)[1])['estimated_usd'])
        self.assertNotIn('private error details', '\n'.join(c.args[0] for c in log.call_args_list))
