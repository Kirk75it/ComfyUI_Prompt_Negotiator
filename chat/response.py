from __future__ import annotations

import json
import re
from typing import Any


def _strip_code_fence(text: str) -> str:
    value = (text or "").strip()
    match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", value, flags=re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else value


def _find_json_object(text: str) -> dict[str, Any] | None:
    value = _strip_code_fence(text)
    decoder = json.JSONDecoder()
    for index, char in enumerate(value):
        if char != "{":
            continue
        try:
            candidate, _ = decoder.raw_decode(value[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(candidate, dict):
            return candidate
    return None


def _key_value(data: dict[str, Any], target: str) -> Any:
    wanted = target.casefold()
    for key, value in data.items():
        if str(key).casefold() == wanted:
            return value
    return None


def _normalize_suggestions(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    if not text:
        return []
    return [text]




PARSER_SYSTEM_INSTRUCTIONS = """
[Prompt Negotiator — parser response contract]
Quando rispondi, restituisci esclusivamente un singolo oggetto JSON valido, senza
markdown, senza code fence e senza testo prima o dopo il JSON. Usa esattamente
questa struttura:
{
  "PROMPT": "qui va inserito il prompt completo creato",
  "SUGGERIMENTI": [
    "qui vanno inseriti tutti i suggerimenti utili per migliorare il prompt"
  ]
}

Regole:
- PROMPT deve contenere esclusivamente il prompt finale da usare per la generazione.
- SUGGERIMENTI deve essere sempre un array di stringhe; può essere vuoto se non ci sono suggerimenti.
- Non aggiungere altre chiavi JSON.
- Non scrivere spiegazioni fuori dall'oggetto JSON.
""".strip()

PARSER_SYSTEM_MARKER = "[Prompt Negotiator — parser response contract]"


def build_effective_system_prompt(user_system_prompt: str | None, *, mode: str = "parser") -> str:
    """Return the system prompt actually sent to the model.

    In parser mode the node-owned JSON response contract is appended after the
    user's system prompt. The user's field remains optional and is stored
    separately from this derived runtime prompt, so sessions do not accumulate
    the contract on every reload.
    """
    base = str(user_system_prompt or "").replace("\x00", "").strip()
    normalized_mode = str(mode or "parser").strip().lower()
    if normalized_mode != "parser":
        return base
    if PARSER_SYSTEM_MARKER in base:
        return base
    if not base:
        return PARSER_SYSTEM_INSTRUCTIONS
    return f"{base}\n\n{PARSER_SYSTEM_INSTRUCTIONS}"


def parse_assistant_response(raw_response: str, *, mode: str = "parser") -> dict[str, Any]:
    """Parse the built-in optional {PROMPT, SUGGERIMENTI} contract.

    ``parser`` is the automatic/default mode. ``normal`` deliberately leaves
    the response untouched so users can parse custom structures elsewhere in
    the workflow (for example with a JSON extraction node).
    """
    raw = str(raw_response or "").strip()
    if str(mode or "parser").strip().lower() != "parser":
        return {"structured": False, "prompt": raw, "suggestions": []}

    data = _find_json_object(raw)
    if data is None:
        return {
            "structured": False,
            "prompt": raw,
            "suggestions": [],
        }

    prompt = _key_value(data, "PROMPT")
    suggestions = _key_value(data, "SUGGERIMENTI")
    prompt_text = str(prompt or "").strip()
    if not prompt_text:
        return {
            "structured": False,
            "prompt": raw,
            "suggestions": [],
        }

    return {
        "structured": True,
        "prompt": prompt_text,
        "suggestions": _normalize_suggestions(suggestions),
    }


def canonical_json_response(prompt: str, suggestions: list[str] | None = None) -> str:
    """Return a stable JSON representation of the built-in parser contract."""
    payload = {"PROMPT": str(prompt or "").strip(), "SUGGERIMENTI": list(suggestions or [])}
    return json.dumps(payload, ensure_ascii=False, indent=2)


def restore_raw_response(content: str, metadata: dict[str, Any] | None = None) -> str:
    """Restore the raw model response kept in message metadata.

    Older parser-mode records may have only the derived prompt/suggestions.
    In that case rebuild a canonical JSON response so the next chat round
    receives structured content again.
    """
    meta = metadata or {}
    raw_response = str(meta.get("raw_response") or "").strip()
    if raw_response:
        return raw_response
    mode = str(meta.get("response_mode", "parser") or "parser").strip().lower()
    if mode == "parser" and bool(meta.get("structured")) and str(meta.get("prompt") or "").strip():
        return canonical_json_response(str(meta.get("prompt") or ""), list(meta.get("suggestions") or []))
    return str(content or "").strip()


def message_metadata(raw_response: str, base: dict[str, Any] | None = None, *, mode: str = "parser") -> dict[str, Any]:
    response_mode = str(mode or "parser").strip().lower()
    if response_mode not in {"parser", "normal"}:
        response_mode = "parser"
    parsed = parse_assistant_response(raw_response, mode=response_mode)
    result = dict(base or {})
    result.update(
        {
            "response_mode": response_mode,
            "structured": parsed["structured"],
            "prompt": parsed["prompt"],
            "suggestions": parsed["suggestions"],
            "raw_response": raw_response,
        }
    )
    return result


def approval_prompt_from_message(content: str, metadata: dict[str, Any] | None = None) -> str:
    mode = str((metadata or {}).get("response_mode", "parser") or "parser").strip().lower()
    if mode == "normal":
        return str(content or "").strip()
    if metadata:
        prompt = str(metadata.get("prompt") or "").strip()
        if prompt:
            return prompt
    return str(parse_assistant_response(content, mode="parser")["prompt"] or "").strip()

