from __future__ import annotations

from typing import Any

from ..errors import GenerationNotCapableError
from ..models import GenerationSettings


class ClipService:
    @staticmethod
    def is_generation_capable(clip: Any) -> tuple[bool, str | None]:
        generate = getattr(clip, "generate", None)
        if not callable(generate):
            return False, "CLIP wrapper non espone generate()."
        model = getattr(clip, "cond_stage_model", None)
        model_generate = getattr(model, "generate", None)
        if not callable(model_generate):
            return False, "Il text encoder sottostante non espone generate()."
        return True, None

    @staticmethod
    def generate_response(
        clip: Any,
        prompt_text: str,
        settings: GenerationSettings,
        *,
        preformatted: bool = False,
        system_prompt: str = "",
        image: Any | None = None,
    ) -> str:
        capable, error = ClipService.is_generation_capable(clip)
        if not capable:
            raise GenerationNotCapableError(error or "Text encoder non generativo.")

        # Deliberately mirror ComfyUI v0.37.4 TextGenerate. The PromptNegotiator
        # must not invent another generation API. A preformatted transcript uses
        # skip_template=True; otherwise the concrete text encoder receives the
        # system prompt through the same tokenizer argument used by TextGenerate.
        tokens = clip.tokenize(
            prompt_text,
            image=image,
            skip_template=preformatted or not settings.use_default_template,
            min_length=1,
            thinking=settings.thinking,
            system_prompt=system_prompt if settings.use_default_template and not preformatted else "",
        )
        generated_ids = clip.generate(
            tokens,
            do_sample=settings.do_sample,
            max_length=settings.max_length,
            temperature=settings.temperature,
            top_k=settings.top_k,
            top_p=settings.top_p,
            min_p=settings.min_p,
            repetition_penalty=settings.repetition_penalty,
            seed=settings.seed,
            presence_penalty=settings.presence_penalty,
            mtp=settings.mtp_value,
        )
        return str(clip.decode(generated_ids)).strip()

    @staticmethod
    def encode_prompt(clip: Any, approved_prompt: str) -> Any:
        tokens = clip.tokenize(approved_prompt)
        return clip.encode_from_tokens_scheduled(tokens)


SERVICE = ClipService()
