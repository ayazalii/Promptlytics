"""
db.py
-----
Module 4: Database Execution (Section 4.3).

Provides a thin wrapper around sqlite3 + pandas:
  - get_connection(): opens (and lazily creates/seeds) the SQLite database.
  - run_query(sql, params): executes a parameterized, read-only query and
    returns (DataFrame, error_message). Never raises -- callers check
    `error` and display it in the UI instead of crashing the app.

Only SELECT statements are ever passed here (sql_builder.py only emits
SELECT templates, and intent_engine.py rejects write/DDL keywords before
that), but run_query() additionally guards against any non-SELECT
statement reaching sqlite3 as a defense-in-depth measure.
"""

import os
import sqlite3

import pandas as pd

import config


def get_connection():
    """
    Open a connection to the Promptlytics SQLite database, creating and
    seeding it on first run if it doesn't exist yet.
    """
    if not os.path.exists(config.DB_PATH):
        os.makedirs(config.DATA_DIR, exist_ok=True)
        # Local import avoids a circular dependency (seed_database imports
        # config but not db) and keeps the seed step out of normal imports.
        import seed_database
        seed_database.seed(config.DB_PATH)

    conn = sqlite3.connect(config.DB_PATH)
    return conn


def run_query(sql: str, params: tuple = ()):
    """
    Execute a read-only SQL query and return (DataFrame, error_message).

    On success, error_message is None. On failure (bad SQL, disallowed
    statement, etc.), the DataFrame is empty and error_message describes
    what went wrong.
    """
    stripped = sql.strip().lstrip("(").strip()
    if not stripped.lower().startswith("select"):
        return pd.DataFrame(), "Only SELECT queries are permitted."

    try:
        conn = get_connection()
        try:
            df = pd.read_sql_query(sql, conn, params=params)
        finally:
            conn.close()
        return df, None
    except (sqlite3.Error, pd.errors.DatabaseError) as exc:
        return pd.DataFrame(), f"Database error: {exc}"
    except Exception as exc:  # pragma: no cover - defensive catch-all
        return pd.DataFrame(), f"Unexpected error: {exc}"


def row_count() -> int:
    """Convenience helper used by app.py to show a 'X records loaded' note."""
    df, err = run_query(f"SELECT COUNT(*) AS n FROM {config.TABLE_NAME}")
    if err or df.empty:
        return 0
    return int(df.iloc[0]["n"])
