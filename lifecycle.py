from __future__ import annotations

import atexit

from .registry import REGISTRY


_REGISTERED = False


def register_lifecycle_handlers() -> None:
    global _REGISTERED
    if _REGISTERED:
        return
    atexit.register(REGISTRY.clear)
    _REGISTERED = True
