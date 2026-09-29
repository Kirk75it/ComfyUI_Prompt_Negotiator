from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ChatState:
    session_id: str | None = None
    encoder_state: str = "UNPREPARED"
    last_error: str | None = None
    final_prompt: str = ""
    title: str = "Nuova sessione"
