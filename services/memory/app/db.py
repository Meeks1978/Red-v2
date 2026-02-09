import os
import sqlite3
from pathlib import Path

DB_PATH = os.getenv("RED_MEMORY_DB", "/data/red_memory.sqlite")

def connect() -> sqlite3.Connection:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def apply_migration(conn: sqlite3.Connection, sql_path: str) -> None:
    with open(sql_path, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()
