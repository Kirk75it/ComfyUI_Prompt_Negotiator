from __future__ import annotations


class PromptNegotiatorError(Exception):
    """Base error for the plugin."""

    code = "PROMPT_NEGOTIATOR_ERROR"


class ValidationError(PromptNegotiatorError):
    code = "VALIDATION_ERROR"


class SessionNotFoundError(PromptNegotiatorError):
    code = "SESSION_NOT_FOUND"


class RuntimeNotPreparedError(PromptNegotiatorError):
    code = "ENCODER_NOT_PREPARED"


class GenerationNotCapableError(PromptNegotiatorError):
    code = "GENERATION_NOT_CAPABLE"


class ClipIdentityError(PromptNegotiatorError):
    code = "CLIP_IDENTITY_ERROR"


class TemplateError(PromptNegotiatorError):
    code = "TEMPLATE_ERROR"
