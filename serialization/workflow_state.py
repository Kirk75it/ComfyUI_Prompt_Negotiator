from __future__ import annotations

from ..config import CONFIG


def normalize_prompt_text(value: str | None) -> str:
    if value is None:
        return ""
    value = str(value).replace("\x00", "")
    return value[: CONFIG.max_approved_prompt_chars]


def normalize_session_title(value: str | None) -> str:
    if value is None:
        return "Nuova sessione"
    value = " ".join(str(value).split())
    if not value:
        return "Nuova sessione"
    return value[: CONFIG.max_title_chars]
