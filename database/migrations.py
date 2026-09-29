from __future__ import annotations

import sqlite3

from .schema import SCHEMA_SQL

TARGET_VERSION = 1


def migrate(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA_SQL)
    connection.execute(
        "INSERT OR REPLACE INTO schema_meta(key, value) VALUES('version', ?)",
        (str(TARGET_VERSION),),
    )
    connection.commit()
