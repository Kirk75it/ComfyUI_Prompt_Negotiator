from __future__ import annotations

from typing_extensions import override

from comfy_api.latest import ComfyExtension, io

from .database.repository import REPOSITORY
from .clip.qwen25_compat import install_qwen25_vl_compat
from .lifecycle import register_lifecycle_handlers
from .node import PromptNegotiator
from .system_prompt import SystemPrompt
from .routes import register_routes


class PromptNegotiatorExtension(ComfyExtension):
    @override
    async def on_load(self) -> None:
        # Import-time initialization is intentionally minimal; this is the
        # explicit extension lifecycle hook used to register persistent state
        # and runtime cleanup.
        install_qwen25_vl_compat()
        REPOSITORY.initialize()
        register_routes()
        register_lifecycle_handlers()

    @override
    async def get_node_list(self) -> list[type[io.ComfyNode]]:
        return [SystemPrompt, PromptNegotiator]


async def comfy_entrypoint() -> PromptNegotiatorExtension:
    return PromptNegotiatorExtension()
