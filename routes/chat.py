from __future__ import annotations
import asyncio
import logging
from dataclasses import asdict
from aiohttp import web
from ..chat.service import ChatService
from ..config import CONFIG
from ..errors import GenerationNotCapableError, PromptNegotiatorError, RuntimeNotPreparedError, SessionNotFoundError, ValidationError
from ..models import GenerationSettings
from ..registry import REGISTRY
from ..database.repository import REPOSITORY
from ..clip.service import SERVICE as CLIP_SERVICE
from ..chat.response import build_effective_system_prompt, message_metadata

CHAT_SERVICE = ChatService(REPOSITORY)
LOGGER = logging.getLogger("PromptNegotiator.Chat")

_GENERATION_LOCK: asyncio.Lock | None = None


def generation_lock() -> asyncio.Lock:
    global _GENERATION_LOCK
    if _GENERATION_LOCK is None:
        _GENERATION_LOCK = asyncio.Lock()
    return _GENERATION_LOCK


def _json_error(exc: Exception, status: int = 400) -> web.Response:
    code = getattr(exc, "code", "PROMPT_NEGOTIATOR_ERROR")
    return web.json_response({"ok": False, "error": {"code": code, "message": str(exc)}}, status=status)


def _parse_settings(payload: dict, fallback: dict | None = None) -> GenerationSettings:
    fallback = fallback or {}

    def value(name: str, default):
        raw = payload.get(name)
        return fallback.get(name, default) if raw is None else raw
    sampling = value("sampling_mode", "off")
    if sampling not in {"on", "off"}:
        raise ValidationError("sampling_mode non valido.")
    mtp = value("mtp", "auto")
    if mtp not in {"auto", "off", "2", "3", "4", "5"}:
        raise ValidationError("mtp non valido.")
    max_history = int(value("max_history_messages", CONFIG.default_max_history_messages))
    max_history = max(CONFIG.min_max_history_messages, min(100, max_history))
    max_length = int(value("max_length", CONFIG.default_max_length))
    if not 1 <= max_length <= CONFIG.max_length:
        raise ValidationError("max_length fuori intervallo.")
    temperature = float(value("temperature", 0.7))
    top_k = int(value("top_k", 64))
    top_p = float(value("top_p", 0.95))
    min_p = float(value("min_p", 0.05))
    repetition_penalty = float(value("repetition_penalty", 1.05))
    presence_penalty = float(value("presence_penalty", 0.0))
    if not 0.0 < temperature <= 10.0:
        raise ValidationError("temperature fuori intervallo.")
    if top_k < 0 or top_k > 4096:
        raise ValidationError("top_k fuori intervallo.")
    if not 0.0 <= top_p <= 1.0:
        raise ValidationError("top_p fuori intervallo.")
    if not 0.0 <= min_p <= 1.0:
        raise ValidationError("min_p fuori intervallo.")
    if repetition_penalty <= 0.0 or repetition_penalty > 10.0:
        raise ValidationError("repetition_penalty fuori intervallo.")
    if presence_penalty < -10.0 or presence_penalty > 10.0:
        raise ValidationError("presence_penalty fuori intervallo.")
    return GenerationSettings(
        max_length=max_length,
        sampling_mode=sampling,
        temperature=temperature,
        top_k=top_k,
        top_p=top_p,
        min_p=min_p,
        repetition_penalty=repetition_penalty,
        seed=int(value("seed", 0)),
        presence_penalty=presence_penalty,
        thinking=bool(value("thinking", False)),
        use_default_template=bool(value("use_default_template", True)),
        mtp=mtp,
        max_history_messages=max_history,
    )


async def chat(request: web.Request) -> web.Response:
    try:
        payload = await request.json()
        node_id = str(payload.get("node_id", "")).strip()
        session_id = str(payload.get("session_id", "")).strip()
        message = str(payload.get("message", ""))
        node_id = str(payload.get("node_id", "")).strip()
        entry = REGISTRY.get_or_raise(node_id) if node_id else None
        response_mode_raw = payload.get("response_mode")
        response_mode = str(
            entry.response_mode if response_mode_raw is None and entry is not None else (response_mode_raw or "parser")
        ).strip().lower()
        if response_mode not in {"parser", "normal"}:
            raise ValidationError("response_mode non valido. Usa parser oppure normal.")
        supplied_system_prompt = payload.get("system_prompt", None)
        system_prompt = "" if supplied_system_prompt is None else str(supplied_system_prompt)

        if not node_id:
            raise ValidationError("node_id mancante.")
        if not session_id:
            raise ValidationError("session_id mancante.")
        if not message.strip():
            raise ValidationError("Il messaggio non può essere vuoto.")
        if len(message) > CONFIG.max_message_chars:
            raise ValidationError("Messaggio troppo lungo.")

        settings = _parse_settings(payload, entry.generation_settings)

        if supplied_system_prompt is None:
            system_prompt = entry.system_prompt

        # The user-facing system_prompt remains optional and is stored as the
        # user's own text. In parser mode, derive the effective runtime prompt
        # by appending the node-owned JSON contract exactly once.
        effective_system_prompt = build_effective_system_prompt(
            system_prompt, mode=response_mode
        )
        if len(effective_system_prompt) > CONFIG.max_system_prompt_chars:
            raise ValidationError("System prompt troppo lungo dopo l'aggiunta del contratto parser.")

        if entry.generation_capable is False:
            raise GenerationNotCapableError(
                entry.generation_error or "Il CLIP collegato non è compatibile con la generazione testuale."
            )

        try:
            session = REPOSITORY.get_session(session_id)
        except KeyError as exc:
            raise SessionNotFoundError(session_id) from exc

        REPOSITORY.update_session(
            session_id,
            system_prompt=system_prompt,
            model_name=entry.identity.model_name,
            clip_type=entry.identity.clip_type,
        )

        image_count = 0
        if entry.image is not None:
            try:
                image_count = int(entry.image.shape[0])
            except Exception:
                image_count = 1

        transcript, _ = CHAT_SERVICE.compose_generation_prompt(
            clip=entry.clip,
            identity=entry.identity,
            system_prompt=effective_system_prompt,
            session_id=session_id,
            current_message=message,
            settings=settings,
            image_count=image_count,
        )
        preformatted = transcript.mode != "neutral_transcript"
        tokenizer_system_prompt = effective_system_prompt if not preformatted else ""

        # Qwen2.5-VL on ComfyUI 0.37.4 misses stop_tokens in its config.
        # The compatibility shim is installed at extension load; this runtime
        # call also repairs already-instantiated clips defensively.
        from ..clip.qwen25_compat import patch_loaded_clip
        patch_loaded_clip(entry.clip)

        async with generation_lock():
            response = await asyncio.to_thread(
                CLIP_SERVICE.generate_response,
                entry.clip,
                transcript.text,
                settings,
                preformatted=preformatted,
                system_prompt=tokenizer_system_prompt,
                image=entry.image,
            )

        metadata = message_metadata(
            response,
            mode=response_mode,
            base={
                "template_mode": transcript.mode,
                "image_attached": entry.image is not None,
                "model_name": entry.identity.model_name,
                "clip_type": entry.identity.clip_type,
                "generation_settings": asdict(settings),
            },
        )
        user_record = REPOSITORY.add_message(session_id, "user", message, metadata={})
        assistant_record = REPOSITORY.add_message(session_id, "assistant", response, metadata=metadata)
        REGISTRY.set_last_generated_response(node_id, response)

        session = REPOSITORY.get_session(session_id)
        if session.title == "Nuova sessione":
            title = " ".join(message.split())[: CONFIG.max_title_chars]
            REPOSITORY.update_session(session_id, title=title or "Nuova sessione")

        return web.json_response({
            "ok": True,
            "session_id": session_id,
            "response": response,
            "template_mode": transcript.mode,
            "user_message": {
                "role": user_record.role,
                "content": user_record.content,
                "sequence": user_record.sequence,
                "created_at": user_record.created_at,
                "metadata": user_record.metadata or {},
            },
            "assistant_message": {
                "role": assistant_record.role,
                "content": assistant_record.content,
                "sequence": assistant_record.sequence,
                "created_at": assistant_record.created_at,
                "metadata": assistant_record.metadata or {},
            },
        })
    except RuntimeNotPreparedError as exc:
        return _json_error(exc, 409)
    except GenerationNotCapableError as exc:
        return _json_error(exc, 409)
    except SessionNotFoundError as exc:
        return _json_error(exc, 404)
    except ValidationError as exc:
        return _json_error(exc, 400)
    except Exception as exc:
        return _json_error(exc, 500)