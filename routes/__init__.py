from __future__ import annotations

from aiohttp import web
from server import PromptServer

from .chat import chat
from .encoder import encoder_status, invalidate_encoder, request_nodes_refresh, request_image_refresh
from .health import health
from .database import database_sessions, database_session, database_update_session, database_delete_session
from .sessions import approve_prompt, create_session, get_session, list_sessions, update_session

_REGISTERED = False


def register_routes() -> None:
    global _REGISTERED
    if _REGISTERED:
        return
    routes = PromptServer.instance.routes
    routes.post("/prompt_negotiator/chat")(chat)
    routes.get("/prompt_negotiator/encoder/status")(encoder_status)
    routes.post("/prompt_negotiator/encoder/invalidate")(invalidate_encoder)
    routes.post("/prompt_negotiator/encoder/refresh-nodes")(request_nodes_refresh)
    routes.post("/prompt_negotiator/encoder/refresh-image")(request_image_refresh)
    routes.get("/prompt_negotiator/sessions")(list_sessions)
    routes.post("/prompt_negotiator/sessions")(create_session)
    routes.get("/prompt_negotiator/sessions/{session_id}")(get_session)
    routes.put("/prompt_negotiator/sessions/{session_id}")(update_session)
    routes.post("/prompt_negotiator/sessions/{session_id}/approve")(approve_prompt)
    routes.get("/prompt_negotiator/database/sessions")(database_sessions)
    routes.get("/prompt_negotiator/database/sessions/{session_id}")(database_session)
    routes.put("/prompt_negotiator/database/sessions/{session_id}")(database_update_session)
    routes.delete("/prompt_negotiator/database/sessions/{session_id}")(database_delete_session)
    routes.get("/prompt_negotiator/health")(health)
    _REGISTERED = True


__all__ = ["register_routes"]
