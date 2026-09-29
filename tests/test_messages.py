import unittest

from ComfyUI_Prompt_Negotiator.chat.messages import build_transcript
from ComfyUI_Prompt_Negotiator.models import ChatMessage, ClipIdentity


class TranscriptTests(unittest.TestCase):
    def test_ltx_system_and_history_are_role_formatted(self):
        identity = ClipIdentity(clip_type="ltxv", model_name="LTX2")
        history = [ChatMessage("user", "prima"), ChatMessage("assistant", "risposta")]
        result = build_transcript(None, identity, "Sei un assistente creativo.", history, "ora fai X", thinking=False, use_default_template=True)
        self.assertEqual(result.mode, "gemma3_ltx")
        self.assertIn("<start_of_turn>system", result.text)
        self.assertIn("Sei un assistente creativo.", result.text)
        self.assertIn("<start_of_turn>model", result.text)
        self.assertIn("<start_of_turn>model", result.text)

    def test_qwen_uses_chatml_roles(self):
        identity = ClipIdentity(clip_type="qwen3_vl", model_name="Qwen3-VL")
        result = build_transcript(None, identity, "sys", [], "ciao", thinking=False, use_default_template=True)
        self.assertEqual(result.mode, "qwen_chatml")
        self.assertTrue(result.text.startswith("<|im_start|>system"))
        self.assertIn("<|im_start|>user", result.text)
        self.assertIn("<|im_start|>assistant\n\n<think>\n\n</think>\n\n", result.text)

    def test_unknown_family_keeps_neutral_transcript(self):
        identity = ClipIdentity(clip_type="unknown")
        result = build_transcript(None, identity, "sys", [], "ciao", thinking=False, use_default_template=True)
        self.assertEqual(result.mode, "neutral_transcript")
        self.assertIn("SYSTEM:", result.text)
        self.assertIn("USER:", result.text)
        self.assertIn("ASSISTANT:", result.text)


class VisionTranscriptTests(unittest.TestCase):
    def test_qwen_image_marker(self):
        from ComfyUI_Prompt_Negotiator.chat.messages import build_transcript
        from ComfyUI_Prompt_Negotiator.models import ClipIdentity
        identity = ClipIdentity(clip_type="qwen3vl_8b")
        transcript = build_transcript(None, identity, "sys", [], "descrivi", thinking=False, use_default_template=True, image_count=1)
        self.assertIn("<|vision_start|><|image_pad|><|vision_end|>", transcript.text)

    def test_gemma4_image_marker(self):
        from ComfyUI_Prompt_Negotiator.chat.messages import build_transcript
        from ComfyUI_Prompt_Negotiator.models import ClipIdentity
        identity = ClipIdentity(model_name="gemma4")
        transcript = build_transcript(None, identity, "sys", [], "descrivi", thinking=False, use_default_template=True, image_count=1)
        self.assertIn("<|image><|image|><image|>", transcript.text)
