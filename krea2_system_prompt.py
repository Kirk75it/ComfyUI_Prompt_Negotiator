from .system_prompt import (
    DEFAULT_PROMPT_FILE,
    SystemPrompt,
    available_prompt_files,
    load_system_prompt,
)

# Backward-compatible Python import alias; this module does not register another node.
Krea2SystemPrompt = SystemPrompt
