from __future__ import annotations

import sqlite3
from pathlib import Path

from ..config import CONFIG


SCHEMA_TIMEOUT = 30.0


def open_connection(path: Path | None = None) -> sqlite3.Connection:
    db_path = Path(path or CONFIG.database_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(
        db_path,
        timeout=SCHEMA_TIMEOUT,
        isolation_level=None,
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA busy_timeout = 30000")
    return connection
