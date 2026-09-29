from __future__ import annotations

import uuid

from aiohttp import web

from ..config import CONFIG
from ..database.repository import REPOSITORY
from ..errors import SessionNotFoundError, ValidationError
from ..serialization.workflow_state import normalize_prompt_text, normalize_session_title
from ..chat.response import approval_prompt_from_message, message_metadata, restore_raw_response


def _json_error(exc: Exception, status: int) -> web.Response:
    return web.json_response({"ok": False, "error": {"code": getattr(exc, "code", "ERROR"), "message": str(exc)}}, status=status)


def _session_json(session):
    return {
        "id": session.id,
        "title": session.title,
        "system_prompt": session.system_prompt,
        "final_prompt": session.final_prompt,
        "model_name": session.model_name,
        "clip_type": session.clip_type,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "revision": session.revision,
    }


async def list_sessions(request: web.Request) -> web.Response:
    limit = int(request.query.get("limit", "100"))
    sessions = REPOSITORY.list_sessions(limit)
    return web.json_response({"ok": True, "sessions": [_session_json(s) for s in sessions]})


async def create_session(request: web.Request) -> web.Response:
    try:
        payload = await request.json()
        system_prompt = normalize_prompt_text(payload.get("system_prompt", ""))[: CONFIG.max_system_prompt_chars]
        final_prompt = normalize_prompt_text(payload.get("final_prompt", ""))
        title = normalize_session_title(payload.get("title"))
        session_id = str(uuid.uuid4())
        session = REPOSITORY.create_session(
            session_id,
            title,
            system_prompt,
            final_prompt=final_prompt,
            model_name=payload.get("model_name"),
            clip_type=payload.get("clip_type"),
        )
        return web.json_response({"ok": True, "session": _session_json(session)})
    except Exception as exc:
        return _json_error(exc, 400)


async def get_session(request: web.Request) -> web.Response:
    session_id = request.match_info["session_id"]
    try:
        session = REPOSITORY.get_session(session_id)
        messages = REPOSITORY.get_messages(session_id)
        return web.json_response({
            "ok": True,
            "session": _session_json(session),
            "messages": [
                {
                    "role": m.role,
                    "content": restore_raw_response(m.content, m.metadata),
                    "sequence": m.sequence,
                    "created_at": m.created_at,
                    "metadata": (
                        m.metadata
                        if (m.role != "assistant" or m.metadata)
                        else message_metadata(m.content, mode="parser")
                    ),
                }
                for m in messages
            ],
        })
    except KeyError as exc:
        return _json_error(SessionNotFoundError(session_id), 404)


async def update_session(request: web.Request) -> web.Response:
    session_id = request.match_info["session_id"]
    try:
        payload = await request.json()
        title = payload.get("title")
        system_prompt = payload.get("system_prompt")
        final_prompt = payload.get("final_prompt")
        if title is not None:
            title = normalize_session_title(title)
        if system_prompt is not None:
            system_prompt = normalize_prompt_text(system_prompt)[: CONFIG.max_system_prompt_chars]
        if final_prompt is not None:
            final_prompt = normalize_prompt_text(final_prompt)
        session = REPOSITORY.update_session(
            session_id,
            title=title,
            system_prompt=system_prompt,
            final_prompt=final_prompt,
        )
        return web.json_response({"ok": True, "session": _session_json(session)})
    except KeyError:
        return _json_error(SessionNotFoundError(session_id), 404)
    except Exception as exc:
        return _json_error(exc, 400)


async def approve_prompt(request: web.Request) -> web.Response:
    session_id = request.match_info["session_id"]
    try:
        payload = await request.json()
        node_id = str(payload.get("node_id", "")).strip()
        selected_sequence = payload.get("message_sequence")
        messages = REPOSITORY.get_messages(session_id)

        assistant_messages = [m for m in messages if m.role == "assistant"]
        if not assistant_messages:
            raise ValidationError("Non esiste ancora una risposta dell'agente da approvare.")

        selected = assistant_messages[-1]
        if selected_sequence not in (None, "", 0):
            try:
                selected_sequence = int(selected_sequence)
            except (TypeError, ValueError) as exc:
                raise ValidationError("message_sequence non valido.") from exc
            selected = next((m for m in assistant_messages if m.sequence == selected_sequence), None)
            if selected is None:
                raise ValidationError("Il messaggio selezionato non esiste più nella sessione.")

        final_prompt = approval_prompt_from_message(selected.content, selected.metadata)
        final_prompt = normalize_prompt_text(final_prompt)
        if not final_prompt:
            raise ValidationError("Il messaggio selezionato non contiene un PROMPT approvabile.")

        revision = REPOSITORY.save_approval(
            session_id,
            final_prompt,
            payload.get("model_name"),
            payload.get("clip_type"),
        )
        session = REPOSITORY.get_session(session_id)
        if node_id:
            from ..registry import REGISTRY
            REGISTRY.set_approved_prompt(node_id, final_prompt)
        return web.json_response({
            "ok": True,
            "revision": revision,
            "message_sequence": selected.sequence,
            "session": _session_json(session),
        })
    except KeyError:
        return _json_error(SessionNotFoundError(session_id), 404)
    except Exception as exc:
        return _json_error(exc, 400)
