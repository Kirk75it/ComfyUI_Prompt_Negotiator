from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..models import ChatMessage, ClipIdentity


@dataclass(frozen=True)
class Transcript:
    text: str
    mode: str


def _clean(text: str | None) -> str:
    return (text or "").replace("\x00", "").strip()


def _is_qwen(identity: ClipIdentity) -> bool:
    values = " ".join(
        str(x or "").lower()
        for x in (identity.clip_type, identity.model_name, identity.tokenizer_class, identity.tokenizer_name)
    )
    return "qwen" in values


def _is_ltx(identity: ClipIdentity) -> bool:
    values = " ".join(
        str(x or "").lower()
        for x in (identity.clip_type, identity.model_name, identity.tokenizer_class, identity.tokenizer_name)
    )
    return "ltx" in values


def _is_gemma4(identity: ClipIdentity) -> bool:
    values = " ".join(
        str(x or "").lower()
        for x in (identity.clip_type, identity.model_name, identity.tokenizer_class, identity.tokenizer_name)
    )
    return "gemma4" in values


def _gemma3_ltx(system_prompt: str, history: list[ChatMessage], current: str, thinking: bool, image_count: int = 0) -> str:
    parts: list[str] = []
    system = _clean(system_prompt)
    if system:
        parts.append(f"<start_of_turn>system\n{system}<end_of_turn>")
    for msg in history:
        content = _clean(msg.content)
        if not content:
            continue
        role = "user" if msg.role == "user" else "model"
        parts.append(f"<start_of_turn>{role}\n{content}<end_of_turn>")
    media = "\n<image_soft_token>\n" if image_count > 0 else ""
    parts.append(f"<start_of_turn>user\n{media}{_clean(current)}<end_of_turn>")
    parts.append("<start_of_turn>model\n")
    if thinking:
        parts.append("<think>")
    return "\n".join(parts)


def _gemma4_ltx(system_prompt: str, history: list[ChatMessage], current: str, thinking: bool, image_count: int = 0) -> str:
    # Mirrors ComfyUI v0.37.4 TextGenerateLTX2Prompt role markers.
    parts: list[str] = []
    system = _clean(system_prompt)
    think_prefix = "<|think|>\n" if thinking else ""
    model_open = "" if thinking else "<|channel>final\n"
    if system:
        parts.append(f"<|turn>system\n{think_prefix}{system}<turn|>")
    for msg in history:
        content = _clean(msg.content)
        if not content:
            continue
        role = "user" if msg.role == "user" else "model"
        parts.append(f"<|turn>{role}\n{content}<turn|>")
    media = "<|image><|image|><image|>\n\n" * max(1, image_count) if image_count > 0 else ""
    parts.append(f"<|turn>user\n{media}{_clean(current)}<turn|>")
    parts.append(f"<|turn>model\n{model_open}")
    return "\n".join(parts)


def _qwen(system_prompt: str, history: list[ChatMessage], current: str, thinking: bool, image_count: int = 0) -> str:
    # Qwen3-VL's tokenizer applies a user/assistant template itself.
    # Because this node must include a system turn and a multi-turn history,
    # we build the full ChatML transcript and ask the tokenizer not to wrap it
    # a second time. The exact special tokens come from the tokenizer family.
    parts: list[str] = []
    system = _clean(system_prompt)
    if system:
        parts.append(f"<|im_start|>system\n{system}<|im_end|>")
    for msg in history:
        content = _clean(msg.content)
        if not content:
            continue
        role = "user" if msg.role == "user" else "assistant"
        parts.append(f"<|im_start|>{role}\n{content}<|im_end|>")
    media = "<|vision_start|>" + ("<|image_pad|>" * max(1, image_count)) + "<|vision_end|>\n" if image_count > 0 else ""
    parts.append(f"<|im_start|>user\n{media}{_clean(current)}<|im_end|>")
    parts.append("<|im_start|>assistant\n")
    if not thinking:
        # Mirrors ComfyUI v0.37.4 Qwen3-VL tokenizer behavior when thinking is disabled.
        parts.append("<think>\n\n</think>\n\n")
    return "\n".join(parts)


def _neutral(system_prompt: str, history: list[ChatMessage], current: str) -> str:
    parts: list[str] = []
    system = _clean(system_prompt)
    if system:
        parts.append(f"SYSTEM:\n{system}")
    for msg in history:
        content = _clean(msg.content)
        if not content:
            continue
        label = "USER" if msg.role == "user" else "ASSISTANT"
        parts.append(f"{label}:\n{content}")
    parts.append(f"USER:\n{_clean(current)}")
    parts.append("ASSISTANT:\n")
    return "\n\n".join(parts)


def build_transcript(
    clip: Any,
    identity: ClipIdentity,
    system_prompt: str,
    history: list[ChatMessage],
    current_message: str,
    *,
    thinking: bool,
    image_count: int = 0,
    use_default_template: bool,
) -> Transcript:
    del clip

    if not use_default_template:
        # Match native TextGenerate semantics: disabling the default template
        # means the tokenizer receives raw transcript text and no system template.
        history_without_system = _neutral("", history, current_message)
        return Transcript(history_without_system, "neutral_transcript")

    # Native ComfyUI-specific behavior is preferred over a generic transcript
    # whenever the upstream CLIP identity makes the family identifiable.
    values = " ".join(
        str(x or "").lower()
        for x in (identity.clip_type, identity.model_name, identity.tokenizer_class, identity.tokenizer_name)
    )
    if _is_ltx(identity) or _is_gemma4(identity):
        if "gemma4" in values:
            return Transcript(_gemma4_ltx(system_prompt, history, current_message, thinking, image_count), "gemma4_ltx")
        return Transcript(_gemma3_ltx(system_prompt, history, current_message, thinking, image_count), "gemma3_ltx")
    if _is_qwen(identity):
        return Transcript(_qwen(system_prompt, history, current_message, thinking, image_count), "qwen_chatml")

    # Unknown model family: preserve the conversation in a neutral transcript.
    # When use_default_template is true, ClipService lets the concrete
    # tokenizer apply its native wrapping around this plain transcript.
    return Transcript(_neutral(system_prompt, history, current_message), "neutral_transcript")
