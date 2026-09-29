import unittest

from ComfyUI_Prompt_Negotiator.clip.service import ClipService
from ComfyUI_Prompt_Negotiator.models import GenerationSettings


class FakeCondStage:
    def generate(self, tokens, **kwargs):
        self.last_generate = (tokens, kwargs)
        return [1, 2, 3]


class FakeClip:
    def __init__(self):
        self.cond_stage_model = FakeCondStage()
        self.tokenizer = self
        self.last_tokenize = None
        self.last_options = None

    def tokenize_with_weights(self, text, return_word_ids=False, thinking=False, skip_template=False, min_length=1, system_prompt="", **kwargs):
        return {"text": text, "thinking": thinking, "skip_template": skip_template, "system_prompt": system_prompt}

    def tokenize(self, text, **kwargs):
        self.last_tokenize = text
        self.last_options = kwargs
        return self.tokenize_with_weights(text, **kwargs)

    def generate(self, tokens, **kwargs):
        return self.cond_stage_model.generate(tokens, **kwargs)

    def decode(self, ids):
        return "generated"

    def encode_from_tokens_scheduled(self, tokens):
        return [[tokens]]


class ClipServiceTests(unittest.TestCase):
    def test_generation_capability(self):
        capable, error = ClipService.is_generation_capable(FakeClip())
        self.assertTrue(capable)
        self.assertIsNone(error)

    def test_system_prompt_is_forwarded_to_native_tokenizer(self):
        clip = FakeClip()
        settings = GenerationSettings()
        result = ClipService.generate_response(clip, "ciao", settings, preformatted=False, system_prompt="sei utile")
        self.assertEqual(result, "generated")
        self.assertEqual(clip.last_options["system_prompt"], "sei utile")

    def test_image_is_forwarded_to_tokenizer(self):
        clip = FakeClip()
        settings = GenerationSettings()
        sentinel = object()
        result = ClipService.generate_response(clip, "descrivi", settings, image=sentinel)
        self.assertEqual(result, "generated")
        self.assertIs(clip.last_options["image"], sentinel)

    def test_preformatted_chat_skips_default_template(self):
        clip = FakeClip()
        settings = GenerationSettings()
        text = "<start_of_turn>system\nsys<end_of_turn>"
        result = ClipService.generate_response(clip, text, settings, preformatted=True)
        self.assertEqual(result, "generated")
        self.assertTrue(clip.last_options["skip_template"])

    def test_conditioning_uses_scheduled_encode(self):
        clip = FakeClip()
        result = ClipService.encode_prompt(clip, "a prompt")
        self.assertEqual(result[0][0]["text"], "a prompt")
