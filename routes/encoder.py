from __future__ import annotations

from aiohttp import web

from ..registry import REGISTRY


async def encoder_status(request: web.Request) -> web.Response:
    node_id = str(request.query.get("node_id", "")).strip()
    if not node_id:
        return web.json_response({"ok": False, "error": {"code": "VALIDATION_ERROR", "message": "node_id mancante."}}, status=400)
    REGISTRY.cleanup()
    return web.json_response({"ok": True, **REGISTRY.status(node_id)})


async def invalidate_encoder(request: web.Request) -> web.Response:
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    node_id = str(payload.get("node_id", "")).strip()
    if not node_id:
        return web.json_response({"ok": False, "error": {"code": "VALIDATION_ERROR", "message": "node_id mancante."}}, status=400)
    REGISTRY.invalidate(node_id, release_model=True)
    return web.json_response({"ok": True, "state": "UNPREPARED", "node_id": node_id})


async def request_nodes_refresh(request: web.Request) -> web.Response:
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    node_id = str(payload.get("node_id", "")).strip()
    if not node_id:
        return web.json_response({"ok": False, "error": {"code": "VALIDATION_ERROR", "message": "node_id mancante."}}, status=400)
    try:
        REGISTRY.request_nodes_refresh(node_id)
    except RuntimeError as exc:
        return web.json_response({"ok": False, "error": {"code": "RUNTIME_NOT_PREPARED", "message": str(exc)}}, status=409)
    return web.json_response({"ok": True, "node_id": node_id, "state": "NODES_REFRESH_PENDING"})


async def request_image_refresh(request: web.Request) -> web.Response:
    """Compatibility endpoint retained for cached 1.0.x frontends."""
    return await request_nodes_refresh(request)
