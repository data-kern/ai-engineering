"""Talking to PostgreSQL. Two helpers: `query` to read, `execute` to change. No ORM, plain SQL.

We open a fresh connection for every call. That is slow at scale (a real service would use a
connection pool) but it keeps this file short and easy to read.
"""
import os
import time
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://servicedesk:servicedesk@localhost:5433/servicedesk")
SQL_FOLDER = Path(__file__).parent / "sql"


def connect():
    """One connection whose rows come back as dictionaries. Use it with `with` so it commits and closes."""
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def query(sql, params=()):
    with connect() as conn:
        return conn.execute(sql, params).fetchall()


def query_one(sql, params=()):
    rows = query(sql, params)
    return rows[0] if rows else None


def execute(sql, params=()):
    with connect() as conn:
        conn.execute(sql, params)


def is_reachable():
    try:
        query("SELECT 1")
        return True
    except psycopg.Error:
        return False


def wait_until_reachable(seconds=60):
    """Used at start-up: the database container may need a few seconds longer than our service."""
    deadline = time.time() + seconds
    while time.time() < deadline:
        if is_reachable():
            return
        time.sleep(1)
    raise RuntimeError(f"PostgreSQL not reachable at {DATABASE_URL} after {seconds}s")


def reset():
    """Drop everything and load the schema + sample data again. Run it before each demo scene."""
    with connect() as conn:
        conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        for sql_file in sorted(SQL_FOLDER.glob("*.sql")):
            conn.execute(sql_file.read_text())
