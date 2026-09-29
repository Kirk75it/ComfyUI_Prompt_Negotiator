from __future__ import annotations

from ComfyUI_Prompt_Negotiator.clip.qwen25_compat import patch_loaded_clip, STOP_TOKENS


class Obj:
    pass


def test_patch_loaded_clip_reaches_real_qwen_config():
    config = Obj()
    transformer = Obj()
    transformer.model = Obj()
    transformer.model.config = config
    qwen_wrapper = Obj()
    qwen_wrapper.transformer = transformer
    root = Obj()
    root.qwen25_7b = qwen_wrapper
    patcher = Obj()
    patcher.model = root
    clip = Obj()
    clip.patcher = patcher

    assert patch_loaded_clip(clip)
    assert config.stop_tokens == STOP_TOKENS
