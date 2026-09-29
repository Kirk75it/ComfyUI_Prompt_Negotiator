from __future__ import annotations

from typing import Any


def encode_prompt(clip: Any, text: str) -> Any:
    tokens = clip.tokenize(text)
    return clip.encode_from_tokens_scheduled(tokens)
