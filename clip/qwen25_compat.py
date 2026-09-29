from __future__ import annotations

import logging
from typing import Any

LOGGER = logging.getLogger("PromptNegotiator.Qwen25Compat")

STOP_TOKENS = [151643, 151645]
_PATCH_INSTALLED = False
_ORIGINAL_INIT = None


def install_qwen25_vl_compat() -> bool:
    """Backport the Qwen2.5-VL generation fix needed by ComfyUI 0.37.4.

    ComfyUI 0.37.4 defines Qwen25_7BVLI_Config without stop_tokens and with
    lm_head=False.  The PromptNegotiator needs generate(), so install the
    minimal generation-side compatibility patch before any Qwen2.5-VL model
    instance is constructed.
    """
    global _PATCH_INSTALLED, _ORIGINAL_INIT
    if _PATCH_INSTALLED:
        return True

    try:
        import comfy.text_encoders.llama as llama
    except Exception as exc:  # pragma: no cover - only exercised inside ComfyUI
        LOGGER.warning("Qwen2.5-VL compat non installato: %s", exc)
        return False

    config_cls = getattr(llama, "Qwen25_7BVLI_Config", None)
    model_cls = getattr(llama, "Qwen25_7BVLI", None)
    if config_cls is None or model_cls is None:
        return False

    # Runtime-compatible backport of the missing core field.
    if not hasattr(config_cls, "stop_tokens"):
        config_cls.stop_tokens = list(STOP_TOKENS)
        LOGGER.info("[Qwen25Compat] aggiunto Qwen25_7BVLI_Config.stop_tokens=%s", STOP_TOKENS)

    # Qwen2.5-VL uses an untied output projection.  The v0.37.4 config has
    # lm_head=False, so Llama2_ does not create the real output projection.
    # Enable it before construction; otherwise output.weight cannot be loaded.
    if not getattr(model_cls, "_prompt_negotiator_lm_head_patch", False):
        _ORIGINAL_INIT = model_cls.__init__

        def patched_init(self, config_dict, dtype, device, operations):
            config_dict = dict(config_dict)
            config_dict["lm_head"] = True
            _ORIGINAL_INIT(self, config_dict, dtype, device, operations)
            # Defensive instance-level backport as well.
            if not hasattr(self.model.config, "stop_tokens"):
                self.model.config.stop_tokens = list(STOP_TOKENS)

        model_cls.__init__ = patched_init
        model_cls._prompt_negotiator_lm_head_patch = True
        LOGGER.info("[Qwen25Compat] Qwen25_7BVLI lm_head=True patch installato")

    _PATCH_INSTALLED = True
    return True


def patch_loaded_clip(clip: Any) -> bool:
    """Patch an already-instantiated Qwen2.5-VL CLIP instance defensively."""
    if clip is None:
        return False

    try:
        patcher = getattr(clip, "patcher", None)
        root = getattr(patcher, "model", None)

        # QwenImageTEModel_ is an SD1ClipModel named 'qwen25_7b'.
        qwen_wrapper = getattr(root, "qwen25_7b", None)
        transformer = getattr(qwen_wrapper, "transformer", None)
        config = getattr(getattr(transformer, "model", None), "config", None)
        if config is None:
            return False

        changed = False
        if not hasattr(config, "stop_tokens"):
            config.stop_tokens = list(STOP_TOKENS)
            changed = True
            LOGGER.info("[Qwen25Compat] patch runtime config.stop_tokens=%s", STOP_TOKENS)

        return changed or True
    except Exception as exc:
        LOGGER.warning("[Qwen25Compat] patch runtime fallita: %s", exc)
        return False
