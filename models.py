from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class ClipIdentity:
    clip_type: str | None = None
    model_name: str | None = None
    loader_node_id: str | None = None
    loader_class: str | None = None
    tokenizer_class: str | None = None
    tokenizer_name: str | None = None


@dataclass
class RuntimeEntry:
    node_id: str
    clip: Any
    identity: ClipIdentity
    bound_at: float
    image: Any | None = None
    system_prompt: str = ""
    approved_prompt: str = ""
    last_generated_response: str = ""
    generation_capable: bool | None = None
    generation_error: str | None = None
    response_mode: str = "parser"
    generation_settings: dict[str, Any] = field(default_factory=dict)


@dataclass
class ChatMessage:
    role: str
    content: str
    sequence: int = 0
    created_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] | None = None


@dataclass
class Session:
    id: str
    title: str
    system_prompt: str
    final_prompt: str
    model_name: str | None
    clip_type: str | None
    created_at: str
    updated_at: str
    revision: int = 0


@dataclass(frozen=True)
class GenerationSettings:
    max_length: int = 512
    sampling_mode: str = "off"
    temperature: float = 0.7
    top_k: int = 64
    top_p: float = 0.95
    min_p: float = 0.05
    repetition_penalty: float = 1.05
    seed: int | None = 0
    presence_penalty: float = 0.0
    thinking: bool = False
    use_default_template: bool = True
    mtp: str = "auto"
    max_history_messages: int = 8

    @property
    def do_sample(self) -> bool:
        return self.sampling_mode == "on"

    @property
    def mtp_value(self) -> bool | int:
        if self.mtp == "off":
            return False
        if self.mtp == "auto":
            return True
        return int(self.mtp)
