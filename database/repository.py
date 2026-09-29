from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from pathlib import Path
from typing import Any

from ..models import ChatMessage, Session, utc_now_iso


def _restore_raw_response(content: str, metadata: dict[str, Any] | None) -> str:
    # Lazy import avoids the database <-> chat package import cycle.
    from ..chat.response import restore_raw_response
    return restore_raw_response(content, metadata)
from .connection import open_connection
from .migrations import migrate


class SessionRepository:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path
        self._initialized = False

    def initialize(self) -> None:
        if self._initialized:
            return
        self._initialize()
        self._initialized = True

    def _initialize(self) -> None:
        conn = open_connection(self.db_path)
        try:
            migrate(conn)
        finally:
            conn.close()

    def create_session(
        self,
        session_id: str,
        title: str,
        system_prompt: str,
        final_prompt: str = "",
        model_name: str | None = None,
        clip_type: str | None = None,
    ) -> Session:
        self.initialize()
        now = utc_now_iso()
        conn = open_connection(self.db_path)
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """
                INSERT INTO sessions
                (id, title, system_prompt, final_prompt, model_name, clip_type, created_at, updated_at, revision)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
                """,
                (session_id, title, system_prompt, final_prompt, model_name, clip_type, now, now),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        return self.get_session(session_id)

    def get_session(self, session_id: str) -> Session:
        self.initialize()
        conn = open_connection(self.db_path)
        try:
            row = conn.execute(
                "SELECT * FROM sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
            if row is None:
                raise KeyError(session_id)
            return Session(
                id=row["id"],
                title=row["title"],
                system_prompt=row["system_prompt"],
                final_prompt=row["final_prompt"],
                model_name=row["model_name"],
                clip_type=row["clip_type"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                revision=row["revision"],
            )
        finally:
            conn.close()

    def list_sessions(self, limit: int = 100) -> list[Session]:
        self.initialize()
        limit = max(1, min(500, int(limit)))
        conn = open_connection(self.db_path)
        try:
            rows = conn.execute(
                "SELECT * FROM sessions ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [
                Session(
                    id=row["id"],
                    title=row["title"],
                    system_prompt=row["system_prompt"],
                    final_prompt=row["final_prompt"],
                    model_name=row["model_name"],
                    clip_type=row["clip_type"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    revision=row["revision"],
                )
                for row in rows
            ]
        finally:
            conn.close()

    def update_session(
        self,
        session_id: str,
        *,
        title: str | None = None,
        system_prompt: str | None = None,
        final_prompt: str | None = None,
        model_name: str | None = None,
        clip_type: str | None = None,
    ) -> Session:
        self.initialize()
        existing = self.get_session(session_id)
        values = {
            "title": existing.title if title is None else title,
            "system_prompt": existing.system_prompt if system_prompt is None else system_prompt,
            "final_prompt": existing.final_prompt if final_prompt is None else final_prompt,
            "model_name": existing.model_name if model_name is None else model_name,
            "clip_type": existing.clip_type if clip_type is None else clip_type,
        }
        now = utc_now_iso()
        conn = open_connection(self.db_path)
        try:
            conn.execute(
                """
                UPDATE sessions
                SET title = ?, system_prompt = ?, final_prompt = ?, model_name = ?, clip_type = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    values["title"],
                    values["system_prompt"],
                    values["final_prompt"],
                    values["model_name"],
                    values["clip_type"],
                    now,
                    session_id,
                ),
            )
            conn.commit()
        finally:
            conn.close()
        return self.get_session(session_id)

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> ChatMessage:
        self.initialize()
        if role not in {"user", "assistant"}:
            raise ValueError("Invalid message role")
        conn = open_connection(self.db_path)
        try:
            row = conn.execute(
                "SELECT COALESCE(MAX(sequence), 0) + 1 AS next_sequence FROM messages WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            sequence = int(row["next_sequence"])
            created_at = utc_now_iso()
            conn.execute(
                """
                INSERT INTO messages(session_id, sequence, role, content, created_at, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    sequence,
                    role,
                    content,
                    created_at,
                    json.dumps(metadata or {}, ensure_ascii=False),
                ),
            )
            conn.execute(
                "UPDATE sessions SET updated_at = ? WHERE id = ?",
                (created_at, session_id),
            )
            conn.commit()
            return ChatMessage(role=role, content=content, sequence=sequence, created_at=created_at, metadata=metadata or {})
        finally:
            conn.close()

    def get_message(self, session_id: str, sequence: int) -> ChatMessage:
        self.initialize()
        conn = open_connection(self.db_path)
        try:
            row = conn.execute(
                "SELECT * FROM messages WHERE session_id = ? AND sequence = ?",
                (session_id, int(sequence)),
            ).fetchone()
            if row is None:
                raise KeyError((session_id, sequence))
            metadata = json.loads(row["metadata_json"] or "{}")
            return ChatMessage(
                role=row["role"],
                content=_restore_raw_response(row["content"], metadata),
                sequence=row["sequence"],
                created_at=row["created_at"],
                metadata=metadata,
            )
        finally:
            conn.close()

    def get_messages(self, session_id: str, limit: int | None = None) -> list[ChatMessage]:
        conn = open_connection(self.db_path)
        try:
            if limit is None:
                rows = conn.execute(
                    "SELECT * FROM messages WHERE session_id = ? ORDER BY sequence ASC",
                    (session_id,),
                ).fetchall()
            else:
                limit = max(1, int(limit))
                rows = conn.execute(
                    """
                    SELECT * FROM messages
                    WHERE session_id = ?
                    ORDER BY sequence DESC
                    LIMIT ?
                    """,
                    (session_id, limit),
                ).fetchall()
                rows = list(reversed(rows))
            result: list[ChatMessage] = []
            for row in rows:
                metadata = json.loads(row["metadata_json"] or "{}")
                result.append(
                    ChatMessage(
                        role=row["role"],
                        content=_restore_raw_response(row["content"], metadata),
                        sequence=row["sequence"],
                        created_at=row["created_at"],
                        metadata=metadata,
                    )
                )
            return result
        finally:
            conn.close()

    def save_approval(
        self,
        session_id: str,
        final_prompt: str,
        model_name: str | None,
        clip_type: str | None,
    ) -> int:
        self.initialize()
        now = utc_now_iso()
        conn = open_connection(self.db_path)
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT revision FROM sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
            if row is None:
                raise KeyError(session_id)
            revision = int(row["revision"]) + 1
            conn.execute(
                """
                UPDATE sessions
                SET final_prompt = ?, revision = ?, updated_at = ?, model_name = ?, clip_type = ?
                WHERE id = ?
                """,
                (final_prompt, revision, now, model_name, clip_type, session_id),
            )
            conn.execute(
                """
                INSERT INTO prompt_revisions
                (session_id, revision, final_prompt, created_at, model_name, clip_type)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (session_id, revision, final_prompt, now, model_name, clip_type),
            )
            conn.commit()
            return revision
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def delete_session(self, session_id: str) -> None:
        self.initialize()
        conn = open_connection(self.db_path)
        try:
            conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            conn.commit()
        finally:
            conn.close()

    def export_session(self, session_id: str) -> dict[str, Any]:
        self.initialize()
        session = self.get_session(session_id)
        return {
            "session": asdict(session),
            "messages": [asdict(msg) for msg in self.get_messages(session_id)],
        }


REPOSITORY = SessionRepository()
