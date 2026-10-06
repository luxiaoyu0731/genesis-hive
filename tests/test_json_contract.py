import unittest
from backend.core.utils import extract_json, extract_json_safe

class JsonContractTests(unittest.TestCase):
    def test_valid_forms(self):
        for text in ['{"ok": true}', '```json\n{"ok": true}\n```', 'result: {"ok": true}']:
            self.assertEqual(extract_json(text), {"ok": True})
    def test_non_objects_rejected(self):
        for text in ['[]', '[{"ok":true}]', '1', 'null', '```json\n[]\n```', 'broken']:
            with self.assertRaises(ValueError): extract_json(text)
            self.assertEqual(extract_json_safe(text), {})
