import sys
import types
import unittest
from pathlib import Path

ROOT_PARENT = Path(__file__).resolve().parents[1].parent
if str(ROOT_PARENT) not in sys.path:
    sys.path.insert(0, str(ROOT_PARENT))


class _DummyOutput:
    pass


class _DummyInput:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class _DummySchema:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class _DummyNodeOutput:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class _DummyComfyNode:
    pass


io = types.SimpleNamespace(
    ComfyNode=_DummyComfyNode,
    Schema=_DummySchema,
    NodeOutput=_DummyNodeOutput,
    String=types.SimpleNamespace(Output=lambda *a, **k: _DummyOutput()),
    Combo=types.SimpleNamespace(Input=lambda *a, **k: _DummyInput(*a, **k)),
)
comfy_api = types.ModuleType("comfy_api")
latest = types.ModuleType("comfy_api.latest")
latest.io = io
comfy_api.latest = latest
sys.modules.setdefault("comfy_api", comfy_api)
sys.modules.setdefault("comfy_api.latest", latest)

from ComfyUI_Prompt_Negotiator.system_prompt import (
    DEFAULT_PROMPT_FILE,
    SystemPrompt,
    available_prompt_files,
    load_system_prompt,
)


class SystemPromptTests(unittest.TestCase):
    def test_schema_category_and_name(self):
        schema = SystemPrompt.define_schema()
        self.assertEqual(schema.kwargs["category"], "Prompt Navigator")
        self.assertEqual(schema.kwargs["display_name"], "System Prompt")
        self.assertEqual(schema.kwargs["node_id"], "Krea2SystemPrompt")

    def test_schema_has_one_selector_and_one_output(self):
        schema = SystemPrompt.define_schema()
        self.assertEqual(len(schema.kwargs["inputs"]), 1)
        self.assertEqual(len(schema.kwargs["outputs"]), 1)
        selector = schema.kwargs["inputs"][0]
        self.assertEqual(selector.kwargs["default"], DEFAULT_PROMPT_FILE)
        self.assertEqual(list(selector.kwargs["options"]), available_prompt_files())

    def test_expected_preset_files_exist(self):
        files = available_prompt_files()
        self.assertIn("qwen3vl-reverse-analyzer", files)
        self.assertIn("runninghub-krea2-compiler", files)
        self.assertIn("krea2-universal-vision-creator", files)

    def test_execute_reads_selected_file(self):
        for prompt_file in available_prompt_files():
            out = SystemPrompt.execute(prompt_file)
            self.assertEqual(out.args[0], load_system_prompt(prompt_file))
            self.assertTrue(out.args[0].strip())

    def test_unknown_file_falls_back_to_default(self):
        out = SystemPrompt.execute("not-a-real-file")
        self.assertEqual(out.args[0], load_system_prompt(DEFAULT_PROMPT_FILE))

    def test_prompts_are_external_files(self):
        module_text = Path(__file__).resolve().parents[1].joinpath(
            "system_prompt.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("You are a Krea 2 vision analyzer", module_text)
        self.assertNotIn("You are a Krea 2 prompt compiler", module_text)
        self.assertNotIn("You are a Krea 2 universal vision-to-prompt creator", module_text)


if __name__ == "__main__":
    unittest.main()
