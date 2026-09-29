import unittest

from ComfyUI_Prompt_Negotiator.chat.response import approval_prompt_from_message, canonical_json_response, message_metadata, parse_assistant_response, restore_raw_response


class StructuredResponseTests(unittest.TestCase):
    def test_parser_contract_is_appended_when_system_prompt_is_empty(self):
        from ComfyUI_Prompt_Negotiator.chat.response import build_effective_system_prompt, PARSER_SYSTEM_MARKER
        result = build_effective_system_prompt("", mode="parser")
        self.assertIn(PARSER_SYSTEM_MARKER, result)
        self.assertIn("\"PROMPT\"", result)
        self.assertIn("\"SUGGERIMENTI\"", result)

    def test_parser_contract_is_appended_after_user_system_prompt(self):
        from ComfyUI_Prompt_Negotiator.chat.response import build_effective_system_prompt, PARSER_SYSTEM_MARKER
        result = build_effective_system_prompt("Sei un esperto di prompt.", mode="parser")
        self.assertTrue(result.index("Sei un esperto di prompt.") < result.index(PARSER_SYSTEM_MARKER))

    def test_normal_mode_does_not_append_parser_contract(self):
        from ComfyUI_Prompt_Negotiator.chat.response import build_effective_system_prompt, PARSER_SYSTEM_MARKER
        result = build_effective_system_prompt("Sistema personalizzato", mode="normal")
        self.assertEqual(result, "Sistema personalizzato")
        self.assertNotIn(PARSER_SYSTEM_MARKER, result)

    def test_parser_contract_is_not_doubled(self):
        from ComfyUI_Prompt_Negotiator.chat.response import build_effective_system_prompt, PARSER_SYSTEM_INSTRUCTIONS
        result = build_effective_system_prompt(PARSER_SYSTEM_INSTRUCTIONS, mode="parser")
        self.assertEqual(result, PARSER_SYSTEM_INSTRUCTIONS)

    def test_parses_json_object(self):
        result = parse_assistant_response('{"PROMPT":"a portrait","SUGGERIMENTI":["add rim light","try 85mm"]}')
        self.assertTrue(result["structured"])
        self.assertEqual(result["prompt"], "a portrait")
        self.assertEqual(result["suggestions"], ["add rim light", "try 85mm"])

    def test_parses_fenced_json(self):
        result = parse_assistant_response('```json\n{"PROMPT":"portrait","SUGGERIMENTI":"use softer light"}\n```')
        self.assertTrue(result["structured"])
        self.assertEqual(result["prompt"], "portrait")
        self.assertEqual(result["suggestions"], ["use softer light"])

    def test_key_matching_is_case_insensitive(self):
        result = parse_assistant_response('{"prompt":"portrait","suggerimenti":["more detail"]}')
        self.assertTrue(result["structured"])
        self.assertEqual(result["prompt"], "portrait")

    def test_invalid_json_falls_back_to_raw_response(self):
        raw = "not json at all"
        result = parse_assistant_response(raw)
        self.assertFalse(result["structured"])
        self.assertEqual(result["prompt"], raw)
        self.assertEqual(result["suggestions"], [])

    def test_approval_uses_only_prompt(self):
        raw = '{"PROMPT":"ONLY THIS","SUGGERIMENTI":["not this"]}'
        self.assertEqual(approval_prompt_from_message(raw, None), "ONLY THIS")

    def test_normal_mode_keeps_json_raw(self):
        raw = '{"PROMPT":"ONLY THIS","SUGGERIMENTI":["not this"]}'
        result = parse_assistant_response(raw, mode="normal")
        self.assertFalse(result["structured"])
        self.assertEqual(result["prompt"], raw)
        self.assertEqual(result["suggestions"], [])

    def test_metadata_preserves_raw_response(self):
        raw = '{\n  "PROMPT": "ONLY THIS",\n  "SUGGERIMENTI": ["not this"]\n}'
        metadata = message_metadata(raw, mode="parser")
        self.assertEqual(metadata["raw_response"], raw)

    def test_restore_raw_response_from_metadata(self):
        metadata = message_metadata('{"PROMPT":"ONLY THIS","SUGGERIMENTI":["not this"]}', mode="parser")
        self.assertEqual(restore_raw_response("ONLY THIS\n\nSuggerimento", metadata), metadata["raw_response"])

    def test_restore_legacy_parser_message_to_canonical_json(self):
        metadata = {
            "response_mode": "parser",
            "structured": True,
            "prompt": "ONLY THIS",
            "suggestions": ["not this"],
        }
        restored = restore_raw_response("ONLY THIS\n\n• not this", metadata)
        self.assertEqual(restored, canonical_json_response("ONLY THIS", ["not this"]))

    def test_normal_mode_approval_uses_entire_message(self):
        raw = '{"CUSTOM":"whatever"}'
        metadata = message_metadata(raw, mode="normal")
        self.assertEqual(approval_prompt_from_message(raw, metadata), raw)

if __name__ == "__main__":
    unittest.main()
