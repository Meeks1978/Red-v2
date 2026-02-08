from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

DEFAULT_DB_PATH = os.getenv("RED_DB_PATH", "./data/red.db")


def ensure_parent_dir(db_path: str) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)


def connect(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    ensure_parent_dir(db_path)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


@contextmanager
def tx(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """
    Transaction context safe with executescript() and auto-commit calls.
    """
    try:
        conn.execute("BEGIN IMMEDIATE;")
        yield conn
        if conn.in_transaction:
            conn.commit()
    except Exception:
        if conn.in_transaction:
            conn.rollback()
        raise
