from __future__ import annotations

from aiohttp import web

from ..config import CONFIG
from ..database.repository import REPOSITORY
from ..errors import SessionNotFoundError
from ..serialization.workflow_state import normalize_prompt_text, normalize_session_title


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


def _json_error(exc: Exception, status: int) -> web.Response:
    return web.json_response({"ok": False, "error": {"code": getattr(exc, "code", "ERROR"), "message": str(exc)}}, status=status)


async def database_sessions(request: web.Request) -> web.Response:
    try:
        limit = int(request.query.get("limit", "200"))
        sessions = REPOSITORY.list_sessions(limit)
        return web.json_response({"ok": True, "sessions": [_session_json(s) for s in sessions]})
    except Exception as exc:
        return _json_error(exc, 400)


async def database_session(request: web.Request) -> web.Response:
    sid = request.match_info["session_id"]
    try:
        session = REPOSITORY.get_session(sid)
        messages = REPOSITORY.get_messages(sid)
        return web.json_response({
            "ok": True,
            "session": _session_json(session),
            "messages": [{
                "role": m.role,
                "content": m.content,
                "sequence": m.sequence,
                "created_at": m.created_at,
            } for m in messages],
        })
    except KeyError:
        return _json_error(SessionNotFoundError(sid), 404)


async def database_update_session(request: web.Request) -> web.Response:
    sid = request.match_info["session_id"]
    try:
        payload = await request.json()
        session = REPOSITORY.update_session(
            sid,
            title=normalize_session_title(payload.get("title")) if payload.get("title") is not None else None,
            system_prompt=normalize_prompt_text(payload["system_prompt"])[:CONFIG.max_system_prompt_chars] if "system_prompt" in payload else None,
            final_prompt=normalize_prompt_text(payload["final_prompt"])[:CONFIG.max_approved_prompt_chars] if "final_prompt" in payload else None,
            model_name=payload.get("model_name") if "model_name" in payload else None,
            clip_type=payload.get("clip_type") if "clip_type" in payload else None,
        )
        return web.json_response({"ok": True, "session": _session_json(session)})
    except KeyError:
        return _json_error(SessionNotFoundError(sid), 404)
    except Exception as exc:
        return _json_error(exc, 400)


async def database_delete_session(request: web.Request) -> web.Response:
    sid = request.match_info["session_id"]
    try:
        REPOSITORY.delete_session(sid)
        return web.json_response({"ok": True, "deleted": sid})
    except Exception as exc:
        return _json_error(exc, 400)
