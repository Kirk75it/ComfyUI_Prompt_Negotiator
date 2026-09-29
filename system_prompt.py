from __future__ import annotations

from pathlib import Path

from comfy_api.latest import io


SYSTEM_PROMPT_DIR = Path(__file__).resolve().parent / "SystemPrompt"
DEFAULT_PROMPT_FILE = "qwen3vl-reverse-analyzer"


def available_prompt_files() -> list[str]:
    """Return the available .txt system-prompt names without extensions."""
    SYSTEM_PROMPT_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(
        path.stem
        for path in SYSTEM_PROMPT_DIR.iterdir()
        if path.is_file() and path.suffix.lower() == ".txt"
    )


def _default_prompt_file(files: list[str]) -> str:
    if DEFAULT_PROMPT_FILE in files:
        return DEFAULT_PROMPT_FILE
    return files[0] if files else ""


def load_system_prompt(prompt_file: str) -> str:
    """Load one system prompt from SystemPrompt using UTF-8."""
    files = available_prompt_files()
    if prompt_file not in files:
        raise ValueError(
            f"System prompt non trovato: {prompt_file!r}. "
            f"File disponibili: {', '.join(files) if files else 'nessuno'}"
        )
    return (SYSTEM_PROMPT_DIR / f"{prompt_file}.txt").read_text(encoding="utf-8")


class SystemPrompt(io.ComfyNode):
    """Simple file-based system-prompt selector for Prompt Navigator.

    Drop additional UTF-8 .txt files into SystemPrompt/ to make them available
    as new selector entries after ComfyUI reloads the node definition.
    """

    @classmethod
    def define_schema(cls) -> io.Schema:
        prompt_files = available_prompt_files()
        default = _default_prompt_file(prompt_files)

        # The package ships with presets, but keep a safe fallback for a user
        # who empties the directory while developing custom prompts.
        options = prompt_files or [""]

        return io.Schema(
            node_id="Krea2SystemPrompt",
            display_name="System Prompt",
            category="Prompt Navigator",
            description=(
                "Carica un system prompt da un file .txt nella cartella "
                "SystemPrompt e lo restituisce come testo."
            ),
            inputs=[
                io.Combo.Input(
                    "prompt_type",
                    options=options,
                    default=default,
                    tooltip=(
                        "Seleziona il file .txt dalla cartella SystemPrompt. "
                        "Puoi aggiungere altri file senza modificare il codice."
                    ),
                ),
            ],
            outputs=[io.String.Output(display_name="System Prompt")],
        )

    @classmethod
    def execute(cls, prompt_type: str) -> io.NodeOutput:
        prompt_file = str(prompt_type or "").strip()
        files = available_prompt_files()
        prompt_file = prompt_file if prompt_file in files else _default_prompt_file(files)
        if not prompt_file:
            raise ValueError(
                "La cartella SystemPrompt non contiene file .txt utilizzabili."
            )
        return io.NodeOutput(load_system_prompt(prompt_file))
