import unittest
from ComfyUI_Prompt_Negotiator.serialization.workflow_state import normalize_prompt_text, normalize_session_title


class SerializationTests(unittest.TestCase):
    def test_removes_nulls(self):
        self.assertEqual(normalize_prompt_text("a\x00b"), "ab")

    def test_title_whitespace(self):
        self.assertEqual(normalize_session_title("  A   B  "), "A B")
