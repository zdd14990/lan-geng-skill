"""Offline structural tests; these do not score humor quality."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import re
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('meme_search', ROOT / 'scripts/search.py')
search = importlib.util.module_from_spec(spec)
spec.loader.exec_module(search)


class SkillTests(unittest.TestCase):
    def test_references_exist(self):
        skill = (ROOT / 'SKILL.md').read_text(encoding='utf-8')
        self.assertTrue(skill.startswith('---\nname: lan-geng\n'))
        for name in ['references/formats.md', 'references/hltv.md', 'references/examples.md', 'scripts/search.py']:
            self.assertIn(name, skill)
            self.assertTrue((ROOT / name).is_file())

    def test_output_examples_have_no_category_prefix(self):
        text = (ROOT / 'references/examples.md').read_text(encoding='utf-8')
        examples = text.split('## 反例')[0]
        self.assertIsNone(re.search(r'(?m)^\d+\.\s', examples))
        self.assertIsNone(re.search(r'(?m)^\*\*[^\n]+\*\*：', examples))
        for line in examples.splitlines():
            if 'HLTV' in line and not line.startswith(('#', '以下')):
                self.assertTrue(line.startswith('【HLTV】'), line)

    def test_search_known_record(self):
        output = io.StringIO()
        with patch.object(sys, 'argv', ['search.py', '--id', '12374']), contextlib.redirect_stdout(output):
            search.main()
        lines = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual(lines[0]['matched'], 1)
        self.assertEqual(lines[1]['id'], 12374)
        self.assertTrue(lines[1]['text'].startswith('【HLTV】'))

    def test_search_limit_validation(self):
        with patch.object(sys, 'argv', ['search.py', 'HLTV', '--limit', '0']), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as caught:
                search.main()
        self.assertEqual(caught.exception.code, 2)


if __name__ == '__main__':
    unittest.main()
