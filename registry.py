from __future__ import annotations

import logging
import threading
import time
from dataclasses import asdict
from typing import Any

from .config import CONFIG
from .models import ClipIdentity, RuntimeEntry

LOGGER = logging.getLogger("PromptNegotiator")


class RuntimeRegistry:
    """Runtime-only bindings used by live HTTP routes.

    The registry intentionally owns a strong CLIP reference while a node is
    prepared. The registry never unloads, detaches, or unpatches the CLIP model:
    model lifetime and device placement remain exclusively under ComfyUI's
    model manager.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._entries: dict[str, RuntimeEntry] = {}
        self._nodes_refresh_requests: set[str] = set()

    def bind(
        self,
        node_id: str,
        clip: Any,
        identity: ClipIdentity,
        *,
        system_prompt: str = "",
        approved_prompt: str = "",
        image: Any | None = None,
        update_image: bool = False,
    ) -> RuntimeEntry:
        key = str(node_id)
        with self._lock:
            previous = self._entries.get(key)
            same_clip = previous is not None and previous.clip is clip
            effective_system = system_prompt
            effective_approved = approved_prompt
            effective_response = previous.last_generated_response if same_clip else ""
            effective_image = (
                image
                if update_image
                else (previous.image if same_clip else image)
            )
            entry = RuntimeEntry(
                node_id=key,
                clip=clip,
                identity=identity,
                image=effective_image,
                bound_at=time.monotonic(),
                system_prompt=effective_system,
                approved_prompt=effective_approved,
                last_generated_response=effective_response,
            )
            self._entries[key] = entry
        LOGGER.info(
            "[PromptNegotiator] runtime bind node=%s generation_capable=%s identity=%s preserved_response=%s preserved_approved=%s image=%s",
            entry.node_id,
            entry.generation_capable,
            entry.identity,
            bool(entry.last_generated_response),
            bool(entry.approved_prompt),
            entry.image is not None,
        )
        return entry

    def invalidate(self, node_id: str, *, release_model: bool = True) -> None:
        """Forget the runtime binding without touching ComfyUI's CLIP model.

        ``release_model`` is retained as a compatibility argument for existing
        callers/workflows, but is intentionally ignored. Prompt Negotiator must
        not call ComfyUI model-management unload/detach APIs.
        """
        del release_model
        key = str(node_id)
        with self._lock:
            self._entries.pop(key, None)
            self._nodes_refresh_requests.discard(key)
        LOGGER.info("[PromptNegotiator] runtime invalidated node=%s", key)

    def get(self, node_id: str) -> RuntimeEntry | None:
        key = str(node_id)
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            if time.monotonic() - entry.bound_at > CONFIG.registry_ttl_seconds:
                self._entries.pop(key, None)
                return None
            return entry

    def get_or_raise(self, node_id: str) -> RuntimeEntry:
        from .errors import RuntimeNotPreparedError
        entry = self.get(node_id)
        if entry is None:
            raise RuntimeNotPreparedError("Encoder non preparato. Eseguire Prepare Encoder.")
        return entry

    def set_last_generated_response(self, node_id: str, response: str) -> None:
        with self._lock:
            entry = self._entries.get(str(node_id))
            if entry is not None:
                entry.last_generated_response = str(response or "")
                entry.bound_at = time.monotonic()

    def set_approved_prompt(self, node_id: str, prompt: str) -> None:
        with self._lock:
            entry = self._entries.get(str(node_id))
            if entry is not None:
                entry.approved_prompt = str(prompt or "")
                entry.bound_at = time.monotonic()

    def request_nodes_refresh(self, node_id: str) -> None:
        with self._lock:
            key = str(node_id)
            if key not in self._entries:
                raise RuntimeError("Encoder non preparato. Eseguire prima Prepara / aggiorna CLIP.")
            self._nodes_refresh_requests.add(key)

    def nodes_refresh_requested(self, node_id: str) -> bool:
        with self._lock:
            return str(node_id) in self._nodes_refresh_requests

    def clear_nodes_refresh(self, node_id: str) -> None:
        with self._lock:
            self._nodes_refresh_requests.discard(str(node_id))

    # Backward-compatible aliases for cached 1.0.x frontends.
    def request_image_refresh(self, node_id: str) -> None:
        self.request_nodes_refresh(node_id)

    def image_refresh_requested(self, node_id: str) -> bool:
        return self.nodes_refresh_requested(node_id)

    def clear_image_refresh(self, node_id: str) -> None:
        self.clear_nodes_refresh(node_id)

    def set_image(self, node_id: str, image: Any | None) -> None:
        with self._lock:
            entry = self._entries.get(str(node_id))
            if entry is not None:
                entry.image = image
                entry.bound_at = time.monotonic()

    def cleanup(self) -> None:
        now = time.monotonic()
        stale: list[RuntimeEntry] = []
        with self._lock:
            for key, value in list(self._entries.items()):
                if now - value.bound_at > CONFIG.registry_ttl_seconds:
                    stale.append(self._entries.pop(key))
                    self._nodes_refresh_requests.discard(key)
        del stale  # Dropping registry references is sufficient; ComfyUI owns model lifetime.

    def clear(self) -> None:
        with self._lock:
            entries = list(self._entries.values())
            self._entries.clear()
            self._nodes_refresh_requests.clear()
        del entries  # Dropping registry references is sufficient; ComfyUI owns model lifetime.

    def status(self, node_id: str) -> dict[str, Any]:
        entry = self.get(node_id)
        if entry is None:
            return {
                "state": "UNPREPARED",
                "node_id": str(node_id),
                "generation_capable": False,
                "identity": asdict(ClipIdentity()),
                "image_available": False,
            }
        if entry.generation_capable is True:
            state = "READY"
        elif entry.generation_capable is False:
            state = "READY_ENCODING_ONLY"
        else:
            state = "PREPARED_UNKNOWN"
        return {
            "state": state,
            "node_id": entry.node_id,
            "generation_capable": entry.generation_capable,
            "generation_error": entry.generation_error,
            "system_prompt_bound": bool(entry.system_prompt),
            "image_available": entry.image is not None,
            "identity": asdict(entry.identity),
            "bound_at_monotonic": entry.bound_at,
        }


REGISTRY = RuntimeRegistry()
