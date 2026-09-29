import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT.parent) not in sys.path:
    sys.path.insert(0, str(ROOT.parent))

# Minimal ComfyUI V3 stubs so this test can exercise PromptNegotiator.execute
# without a full ComfyUI installation.
class _DummyInput:
    def __init__(self, *a, **k):
        self.args = a
        self.kwargs = k
class _DummyOutput: pass
class _DummySchema:
    def __init__(self, **kwargs): self.kwargs = kwargs
class _DummyNodeOutput:
    def __init__(self, *args, **kwargs): self.args = args; self.kwargs = kwargs
class _DummyComfyNode:
    hidden = types.SimpleNamespace(unique_id="1", prompt={})
class _DummyHidden:
    unique_id = object()
io = types.SimpleNamespace(
    ComfyNode=_DummyComfyNode, Schema=_DummySchema, NodeOutput=_DummyNodeOutput,
    Clip=types.SimpleNamespace(Input=lambda *a, **k: _DummyInput(*a, **k)),
    Image=types.SimpleNamespace(Input=lambda *a, **k: _DummyInput(*a, **k)),
    Conditioning=types.SimpleNamespace(Output=lambda *a, **k: _DummyOutput()),
    String=types.SimpleNamespace(Input=lambda *a, **k: _DummyInput(*a, **k), Output=lambda *a, **k: _DummyOutput()),
    Int=types.SimpleNamespace(Input=lambda *a, **k: _DummyInput(*a, **k)),
    Float=types.SimpleNamespace(Input=lambda *a, **k: _DummyInput(*a, **k)),
    Boolean=types.SimpleNamespace(Input=lambda *a, **k: _DummyInput(*a, **k)),
    Combo=types.SimpleNamespace(Input=lambda *a, **k: _DummyInput(*a, **k)),
    NumberDisplay=types.SimpleNamespace(number="number"),
    Hidden=_DummyHidden,
)
comfy_api = types.ModuleType("comfy_api")
latest = types.ModuleType("comfy_api.latest")
latest.io = io
comfy_api.latest = latest
sys.modules.setdefault("comfy_api", comfy_api)
sys.modules.setdefault("comfy_api.latest", latest)

import ComfyUI_Prompt_Negotiator.node as node_module
from ComfyUI_Prompt_Negotiator.registry import REGISTRY

class FakeClip:
    def tokenize(self, text, **kwargs): return {"text": text}
    def encode_from_tokens_scheduled(self, tokens): return [[tokens, {}]]
    def generate(self, tokens, **kwargs): return [1, 2]
    def decode(self, ids): return "ok"
    cond_stage_model = types.SimpleNamespace(generate=lambda *a, **k: [1,2])

class ExecuteSmokeTests(unittest.TestCase):
    def tearDown(self):
        REGISTRY.clear()

    def test_execute_uses_supplied_system_prompt_and_does_not_unbind_it(self):
        node_module.PromptNegotiator.hidden = types.SimpleNamespace(unique_id="1", prompt={})
        image = object()
        out = node_module.PromptNegotiator.execute(
            clip=FakeClip(), image=image, system_prompt="SYSTEM OK", approved_prompt="final prompt", response_mode="parser",
            max_history_messages=8, max_length=512, sampling_mode="off",
            temperature=0.7, top_k=64, top_p=0.95, min_p=0.05,
            repetition_penalty=1.05, presence_penalty=0.0, mtp="auto",
            thinking=False, use_default_template=True, seed=0,
        )
        self.assertEqual(out.args[0], "")
        self.assertEqual(out.args[1], "final prompt")
        entry = REGISTRY.get("1")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.system_prompt, "SYSTEM OK")
        self.assertEqual(entry.response_mode, "parser")
        self.assertEqual(entry.generation_settings["max_length"], 512)
        self.assertIs(entry.image, image)

    def test_image_input_is_lazy_and_optional(self):
        schema = node_module.PromptNegotiator.define_schema()
        image_input = schema.kwargs["inputs"][1]
        self.assertTrue(image_input.kwargs.get("lazy"))
        self.assertTrue(image_input.kwargs.get("optional"))

    def test_execute_accepts_missing_optional_image(self):
        node_module.PromptNegotiator.hidden = types.SimpleNamespace(unique_id="1", prompt={})
        out = node_module.PromptNegotiator.execute(
            clip=FakeClip(),
            system_prompt="SYSTEM OK",
            approved_prompt="final prompt", response_mode="parser",
            max_history_messages=8,
            max_length=512,
            sampling_mode="off",
            temperature=0.7,
            top_k=64,
            top_p=0.95,
            min_p=0.05,
            repetition_penalty=1.05,
            presence_penalty=0.0,
            mtp="auto",
            thinking=False,
            use_default_template=True,
            seed=0,
        )
        self.assertEqual(out.args[1], "final prompt")
        entry = REGISTRY.get("1")
        self.assertIsNotNone(entry)
        self.assertIsNone(entry.image)

    def test_execute_signature_image_has_default_none(self):
        import inspect
        sig = inspect.signature(node_module.PromptNegotiator.execute)
        self.assertIs(sig.parameters["image"].default, None)

    def test_lazy_status_does_not_request_image_by_default(self):
        node_module.PromptNegotiator.hidden = types.SimpleNamespace(unique_id="1", prompt={})
        self.assertEqual(node_module.PromptNegotiator.check_lazy_status(None), [])

    def test_lazy_status_requests_image_only_during_nodes_refresh_when_connected(self):
        node_module.PromptNegotiator.hidden = types.SimpleNamespace(
            unique_id="1",
            prompt={"1": {"inputs": {"image": ["5", 0]}}},
        )
        REGISTRY.bind("1", FakeClip(), node_module.ClipIdentity() if hasattr(node_module, "ClipIdentity") else types.SimpleNamespace(), image=None)
        REGISTRY.request_nodes_refresh("1")
        self.assertEqual(node_module.PromptNegotiator.check_lazy_status(None), ["image"])
        REGISTRY.clear_nodes_refresh("1")

    def test_lazy_status_clears_nodes_refresh_when_image_is_not_connected(self):
        node_module.PromptNegotiator.hidden = types.SimpleNamespace(
            unique_id="1",
            prompt={"1": {"inputs": {}}},
        )
        REGISTRY.bind("1", FakeClip(), node_module.ClipIdentity() if hasattr(node_module, "ClipIdentity") else types.SimpleNamespace(), image=None)
        REGISTRY.request_nodes_refresh("1")
        self.assertEqual(node_module.PromptNegotiator.check_lazy_status(None), [])
        self.assertFalse(REGISTRY.nodes_refresh_requested("1"))

    def test_fingerprint_changes_to_force_interactive_reexecution(self):
        fp1 = node_module.PromptNegotiator.fingerprint_inputs()
        fp2 = node_module.PromptNegotiator.fingerprint_inputs()
        self.assertNotEqual(fp1, fp2)

    def test_runtime_settings_are_stored_for_connected_node_values(self):
        node_module.PromptNegotiator.hidden = types.SimpleNamespace(
            unique_id="1",
            prompt={"1": {"inputs": {"system_prompt": ["9", 0], "temperature": ["10", 0]}}},
        )
        node_module.PromptNegotiator.execute(
            clip=FakeClip(),
            system_prompt="external system",
            approved_prompt="external final",
            response_mode="normal",
            max_history_messages=12,
            max_length=777,
            sampling_mode="on",
            temperature=0.42,
            top_k=33,
            top_p=0.88,
            min_p=0.02,
            repetition_penalty=1.1,
            presence_penalty=0.2,
            mtp="3",
            thinking=True,
            use_default_template=False,
            seed=123,
        )
        entry = REGISTRY.get("1")
        self.assertEqual(entry.system_prompt, "external system")
        self.assertEqual(entry.response_mode, "normal")
        self.assertEqual(entry.generation_settings["temperature"], 0.42)
        self.assertEqual(entry.generation_settings["max_history_messages"], 12)

    def test_schema_is_non_idempotent_output_node(self):
        schema = node_module.PromptNegotiator.define_schema()
        self.assertTrue(schema.kwargs.get("is_output_node"))
        self.assertTrue(schema.kwargs.get("not_idempotent"))

if __name__ == "__main__":
    unittest.main()
