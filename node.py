from __future__ import annotations

from typing import Any
import logging

from comfy_api.latest import io

from .clip.identity import resolve_clip_identity
from .clip.service import SERVICE as CLIP_SERVICE
from .config import CONFIG
from .errors import ValidationError
from .registry import REGISTRY
from .serialization.workflow_state import normalize_prompt_text


LOGGER = logging.getLogger("PromptNegotiator")


class PromptNegotiator(io.ComfyNode):
    """Interactive text-generation + CLIP conditioning node.

    The CLIP object is always supplied by the workflow. The node never loads
    or selects a model. Live chat uses that exact CLIP object's generate/decode
    methods; normal execution uses the same object for final conditioning.
    """

    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="PromptNegotiator",
            display_name="Prompt Negotiator",
            category="Prompt Navigator",
            description=(
                "Chat interattiva con il CLIP ricevuto dal workflow e encoding "
                "del prompt approvato. Il nodo non carica modelli."
            ),
            is_output_node=True,
            not_idempotent=True,
            hidden=[io.Hidden.unique_id],
            inputs=[
                io.Clip.Input("clip"),
                io.Image.Input("image", optional=True, lazy=True, tooltip="Immagine opzionale. Viene valutata durante Aggiorna nodi quando collegata.") ,
                io.String.Input(
                    "system_prompt",
                    multiline=True,
                    default="",
                    dynamic_prompts=False,
                    tooltip="Istruzioni iniziali del dialogo. Saranno inserite nel transcript del modello.",
                ),
                io.String.Input(
                    "approved_prompt",
                    multiline=True,
                    default="",
                    dynamic_prompts=False,
                    tooltip="Prompt usato durante la normale esecuzione del workflow.",
                ),
                io.Combo.Input(
                    "response_mode",
                    options=["parser", "normal"],
                    default="parser",
                    tooltip=(
                        "Parser: interpreta il JSON standard {PROMPT, SUGGERIMENTI}. "
                        "Normale: non interpreta la risposta; il testo resta intatto per un eventuale parser esterno."
                    ),
                ),
                io.Int.Input(
                    "max_history_messages",
                    default=8,
                    min=2,
                    max=100,
                    step=1,
                    display_mode=io.NumberDisplay.number,
                    tooltip="Numero massimo di messaggi precedenti inviati al modello durante la chat live.",
                ),
                io.Int.Input(
                    "max_length",
                    default=512,
                    min=1,
                    max=32768,
                    step=1,
                    display_mode=io.NumberDisplay.number,
                    tooltip="Lunghezza massima della risposta generata durante la chat live.",
                ),
                io.Combo.Input(
                    "sampling_mode",
                    options=["off", "on"],
                    default="off",
                ),
                io.Float.Input(
                    "temperature",
                    default=0.7,
                    min=0.01,
                    max=2.0,
                    step=0.01,
                    round=0.01,
                    display_mode=io.NumberDisplay.number,
                ),
                io.Int.Input(
                    "top_k",
                    default=64,
                    min=0,
                    max=1000,
                    step=1,
                    display_mode=io.NumberDisplay.number,
                ),
                io.Float.Input(
                    "top_p",
                    default=0.95,
                    min=0.0,
                    max=1.0,
                    step=0.01,
                    round=0.01,
                    display_mode=io.NumberDisplay.number,
                ),
                io.Float.Input(
                    "min_p",
                    default=0.05,
                    min=0.0,
                    max=1.0,
                    step=0.01,
                    round=0.01,
                    display_mode=io.NumberDisplay.number,
                ),
                io.Float.Input(
                    "repetition_penalty",
                    default=1.05,
                    min=0.1,
                    max=5.0,
                    step=0.01,
                    round=0.01,
                    display_mode=io.NumberDisplay.number,
                ),
                io.Float.Input(
                    "presence_penalty",
                    default=0.0,
                    min=0.0,
                    max=5.0,
                    step=0.01,
                    round=0.01,
                    display_mode=io.NumberDisplay.number,
                ),
                io.Combo.Input(
                    "mtp",
                    options=["auto", "off", "2", "3", "4", "5"],
                    default="auto",
                ),
                io.Boolean.Input(
                    "thinking",
                    default=False,
                    tooltip="Richiede il percorso thinking del text encoder se supportato.",
                ),
                io.Boolean.Input(
                    "use_default_template",
                    default=True,
                    tooltip="Consente al tokenizer specifico del text encoder di applicare il proprio template.",
                ),
                io.Int.Input(
                    "seed",
                    default=0,
                    min=0,
                    max=0xFFFFFFFFFFFFFFFF,
                    step=1,
                    display_mode=io.NumberDisplay.number,
                ),
            ],
            outputs=[
                io.String.Output(display_name="Generated response"),
                io.String.Output(display_name="Approved prompt"),
                io.Conditioning.Output(display_name="Conditioning"),
            ],
        )

    @classmethod
    def fingerprint_inputs(cls, **kwargs):
        # Prompt Negotiator is an interactive output node. Its runtime state
        # can change without any serialized workflow input changing (for
        # example when the user presses "Aggiorna nodi"). Returning a
        # fresh fingerprint prevents ComfyUI from reusing the previous cached
        # output of the same node and guarantees that check_lazy_status() is
        # reached for each explicit refresh.
        import time
        del kwargs
        return str(time.monotonic_ns())

    @classmethod
    def check_lazy_status(cls, image=None, **kwargs):
        """Evaluate IMAGE only during an explicit Update Nodes refresh.

        Prepare / aggiorna CLIP never evaluates IMAGE. Update Nodes queues this
        node without invalidating the prepared CLIP, and requests the lazy image
        dependency only when the workflow actually has an IMAGE link.
        """
        del kwargs
        hidden = cls.hidden
        unique_id = getattr(hidden, "unique_id", None) if hidden is not None else None
        if unique_id is None:
            return []
        node_id = str(unique_id)
        if not REGISTRY.nodes_refresh_requested(node_id):
            return []

        prompt = getattr(hidden, "prompt", None) if hidden is not None else None
        node_data = prompt.get(node_id) if isinstance(prompt, dict) else None
        inputs = node_data.get("inputs", {}) if isinstance(node_data, dict) else {}
        image_value = inputs.get("image")
        image_connected = isinstance(image_value, (list, tuple)) and len(image_value) >= 1
        if image_connected and image is None:
            return ["image"]

        REGISTRY.clear_nodes_refresh(node_id)
        return []

    @staticmethod
    def _input_is_connected(prompt: Any, node_id: str, input_name: str) -> bool:
        if not isinstance(prompt, dict):
            return False
        node_data = prompt.get(str(node_id))
        if not isinstance(node_data, dict):
            return False
        inputs = node_data.get("inputs", {}) or {}
        value = inputs.get(input_name)
        return isinstance(value, (list, tuple)) and len(value) >= 1

    @classmethod
    def execute(
        cls,
        clip: Any,
        system_prompt: str,
        approved_prompt: str,
        response_mode: str,
        max_history_messages: int,
        max_length: int,
        sampling_mode: str,
        temperature: float,
        top_k: int,
        top_p: float,
        min_p: float,
        repetition_penalty: float,
        presence_penalty: float,
        mtp: str,
        thinking: bool,
        use_default_template: bool,
        seed: int,
        image: Any | None = None,
        **_: Any,
    ) -> io.NodeOutput:
        if clip is None:
            raise ValidationError("L'input CLIP è obbligatorio.")

        hidden = cls.hidden
        unique_id = getattr(hidden, "unique_id", None) if hidden is not None else None
        prompt_data = getattr(hidden, "prompt", None) if hidden is not None else None
        if unique_id is None:
            raise ValidationError("UNIQUE_ID non disponibile nel contesto di esecuzione V3.")

        node_id = str(unique_id)
        LOGGER.info("[PromptNegotiator] execute node=%s clip=%s", node_id, type(clip).__name__)
        system = normalize_prompt_text(system_prompt)
        response_mode = str(response_mode or "parser").strip().lower()
        if response_mode not in {"parser", "normal"}:
            raise ValidationError("response_mode non valido. Usa parser oppure normal.")
        if len(system) > CONFIG.max_system_prompt_chars:
            raise ValidationError("Il system prompt supera il limite configurato.")
        approved = normalize_prompt_text(approved_prompt)
        identity = resolve_clip_identity(prompt_data, node_id, clip)
        generation_capable, generation_error = CLIP_SERVICE.is_generation_capable(clip)

        runtime_settings = {
            "max_history_messages": int(max_history_messages),
            "max_length": int(max_length),
            "sampling_mode": str(sampling_mode),
            "temperature": float(temperature),
            "top_k": int(top_k),
            "top_p": float(top_p),
            "min_p": float(min_p),
            "repetition_penalty": float(repetition_penalty),
            "presence_penalty": float(presence_penalty),
            "mtp": str(mtp),
            "thinking": bool(thinking),
            "use_default_template": bool(use_default_template),
            "seed": int(seed),
        }

        image_connected = cls._input_is_connected(prompt_data, node_id, "image")

        entry = REGISTRY.bind(
            node_id,
            clip,
            identity,
            system_prompt=system,
            approved_prompt=approved,
            image=image,
            update_image=(image is not None or not image_connected),
        )
        entry.generation_capable = generation_capable
        entry.response_mode = response_mode
        entry.generation_settings = runtime_settings
        if image is not None:
            REGISTRY.clear_nodes_refresh(node_id)
        entry.generation_error = generation_error
        if not approved:
            # The UI approval route can update the runtime registry before the
            # next queue execution. Preserve that approved value if the widget
            # value has not yet propagated into the queued prompt.
            approved = normalize_prompt_text(entry.approved_prompt)

        conditioning = CLIP_SERVICE.encode_prompt(clip, approved)
        generated_response = entry.last_generated_response
        LOGGER.info(
            "[PromptNegotiator] outputs node=%s generated=%d approved=%d",
            node_id, len(generated_response), len(approved),
        )

        # The live chat is intentionally not executed here. execute() is the
        # deterministic queue path; generation happens only through the custom
        # HTTP route before the workflow is queued.
        return io.NodeOutput(generated_response, approved, conditioning)
