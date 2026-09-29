from __future__ import annotations

from aiohttp import web

from ..database.repository import REPOSITORY
from ..registry import REGISTRY


async def health(request: web.Request) -> web.Response:
    database_ok = True
    try:
        REPOSITORY.list_sessions(limit=1)
    except Exception:
        database_ok = False
    return web.json_response({
        "ok": database_ok,
        "database": database_ok,
        "runtime_registry": True,
    })
