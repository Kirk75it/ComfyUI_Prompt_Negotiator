from __future__ import annotations

import inspect
from dataclasses import asdict
from typing import Any

from ..models import ClipIdentity


CLIP_LOADER_CLASSES = {"CLIPLoader", "DualCLIPLoader"}


def _link_node_id(value: Any) -> str | None:
    if isinstance(value, (list, tuple)) and len(value) >= 1 and isinstance(value[0], (str, int)):
        return str(value[0])
    if isinstance(value, dict):
        for key in ("node_id", "from_node_id", "id"):
            if key in value and isinstance(value[key], (str, int)):
                return str(value[key])
    return None


def _input_links(node: dict[str, Any]) -> list[tuple[str, str]]:
    inputs = node.get("inputs", {}) or {}
    preferred: list[tuple[str, str]] = []
    fallback: list[tuple[str, str]] = []
    for key, value in inputs.items():
        node_id = _link_node_id(value)
        if node_id is None:
            continue
        item = (str(key), node_id)
        low = str(key).lower()
        if low == "clip" or low.startswith("clip") or "clip" in low:
            preferred.append(item)
        else:
            fallback.append(item)
    return preferred + fallback


def find_clip_loaders(prompt: dict[str, Any] | None, current_node_id: str, max_depth: int = 64) -> list[tuple[str, dict[str, Any]]]:
    if not isinstance(prompt, dict):
        return []
    visited: set[str] = set()
    found: list[tuple[str, dict[str, Any]]] = []
    stack: list[tuple[str, int]] = [(str(current_node_id), 0)]
    while stack:
        node_id, depth = stack.pop()
        if node_id in visited or depth > max_depth:
            continue
        visited.add(node_id)
        node = prompt.get(node_id)
        if not isinstance(node, dict):
            continue
        class_type = str(node.get("class_type", ""))
        if class_type in CLIP_LOADER_CLASSES:
            found.append((node_id, node))
            continue
        links = _input_links(node)
        for _, upstream_id in reversed(links):
            stack.append((upstream_id, depth + 1))
    return found


def _tokenizer_details(clip: Any) -> tuple[str | None, str | None]:
    tokenizer = getattr(clip, "tokenizer", None)
    if tokenizer is None:
        return None, None
    cls_name = type(tokenizer).__name__
    tokenizer_name = getattr(tokenizer, "clip_name", None)
    if tokenizer_name is not None:
        tokenizer_name = str(tokenizer_name)
    return cls_name, tokenizer_name


def resolve_clip_identity(prompt: dict[str, Any] | None, node_id: str, clip: Any) -> ClipIdentity:
    clip_type: str | None = None
    model_name: str | None = None
    loader_node_id: str | None = None
    loader_class: str | None = None

    loaders = find_clip_loaders(prompt, str(node_id))
    if loaders:
        loader_node_id, loader = loaders[0]
        loader_class = str(loader.get("class_type", ""))
        inputs = loader.get("inputs", {}) or {}
        raw_type = inputs.get("type")
        if raw_type is not None:
            clip_type = str(raw_type)
        if loader_class == "CLIPLoader":
            raw_name = inputs.get("clip_name")
            if raw_name is not None:
                model_name = str(raw_name)
        elif loader_class == "DualCLIPLoader":
            names = [inputs.get("clip_name1"), inputs.get("clip_name2")]
            model_name = " + ".join(str(x) for x in names if x is not None)

    tokenizer_class, tokenizer_name = _tokenizer_details(clip)
    if model_name is None and tokenizer_name:
        model_name = tokenizer_name

    return ClipIdentity(
        clip_type=clip_type,
        model_name=model_name,
        loader_node_id=loader_node_id,
        loader_class=loader_class,
        tokenizer_class=tokenizer_class,
        tokenizer_name=tokenizer_name,
    )


def tokenizer_accepts(clip: Any, name: str) -> bool:
    tokenizer = getattr(clip, "tokenizer", None)
    method = getattr(tokenizer, "tokenize_with_weights", None)
    if method is None:
        return False
    try:
        signature = inspect.signature(method)
    except (TypeError, ValueError):
        return False
    if name in signature.parameters:
        return True
    return any(p.kind is inspect.Parameter.VAR_KEYWORD for p in signature.parameters.values())


def summarize_identity(identity: ClipIdentity) -> dict[str, Any]:
    return asdict(identity)
