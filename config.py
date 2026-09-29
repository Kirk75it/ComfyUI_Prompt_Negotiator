from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    db_filename: str = "prompt_negotiator.sqlite3"
    db_dirname: str = "prompt_negotiator"
    registry_ttl_seconds: float = 6 * 60 * 60
    default_max_history_messages: int = 8
    min_max_history_messages: int = 2
    max_message_chars: int = 64 * 1024
    max_system_prompt_chars: int = 64 * 1024
    max_approved_prompt_chars: int = 128 * 1024
    max_title_chars: int = 120
    max_length: int = 32768
    default_max_length: int = 512

    @property
    def database_directory(self) -> Path:
        # folder_paths exists only inside the ComfyUI runtime. Keep this import
        # lazy so unit tests and pure helpers can run outside ComfyUI.
        import folder_paths
        return Path(folder_paths.get_user_directory()) / self.db_dirname

    @property
    def database_path(self) -> Path:
        return self.database_directory / self.db_filename


CONFIG = Config()
