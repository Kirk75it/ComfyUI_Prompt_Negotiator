import unittest

from ComfyUI_Prompt_Negotiator.clip.identity import find_clip_loaders, resolve_clip_identity


class IdentityTests(unittest.TestCase):
    def test_finds_clip_loader_upstream(self):
        prompt = {
            "10": {"class_type": "CLIPLoader", "inputs": {"clip_name": "model.safetensors", "type": "ltxv"}},
            "20": {"class_type": "PromptNegotiator", "inputs": {"clip": ["10", 0]}},
        }
        self.assertEqual(find_clip_loaders(prompt, "20")[0][0], "10")

    def test_reads_loader_type_without_loading_a_model(self):
        class FakeTokenizer:
            clip_name = "model.safetensors"

        class FakeClip:
            tokenizer = FakeTokenizer()

        prompt = {
            "10": {"class_type": "CLIPLoader", "inputs": {"clip_name": "model.safetensors", "type": "ltxv"}},
            "20": {"class_type": "PromptNegotiator", "inputs": {"clip": ["10", 0]}},
        }
        identity = resolve_clip_identity(prompt, "20", FakeClip())
        self.assertEqual(identity.clip_type, "ltxv")
        self.assertEqual(identity.model_name, "model.safetensors")
        self.assertEqual(identity.loader_class, "CLIPLoader")
