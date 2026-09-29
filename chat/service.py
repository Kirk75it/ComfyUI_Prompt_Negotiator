from __future__ import annotations

from ..database.repository import SessionRepository
from ..errors import SessionNotFoundError
from ..models import ChatMessage, GenerationSettings
from .messages import Transcript, build_transcript


class ChatService:
    def __init__(self, repository: SessionRepository) -> None:
        self.repository = repository

    def get_history(self, session_id: str, limit: int) -> list[ChatMessage]:
        try:
            return self.repository.get_messages(session_id, limit=limit)
        except KeyError as exc:
            raise SessionNotFoundError(session_id) from exc

    def compose_generation_prompt(
        self,
        clip,
        identity,
        system_prompt: str,
        session_id: str,
        current_message: str,
        settings: GenerationSettings,
        image_count: int = 0,
    ) -> tuple[Transcript, object]:
        try:
            session = self.repository.get_session(session_id)
        except KeyError as exc:
            raise SessionNotFoundError(session_id) from exc
        history = self.repository.get_messages(session_id, limit=settings.max_history_messages)
        transcript = build_transcript(
            clip,
            identity,
            system_prompt,
            history,
            current_message,
            thinking=settings.thinking,
            use_default_template=settings.use_default_template,
            image_count=image_count,
        )
        return transcript, session


__all__ = ["ChatService"]
