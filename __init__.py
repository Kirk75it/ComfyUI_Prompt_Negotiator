WEB_DIRECTORY = "./web"


async def comfy_entrypoint():
    from .extension import PromptNegotiatorExtension
    return PromptNegotiatorExtension()


__all__ = ["WEB_DIRECTORY", "comfy_entrypoint"]
