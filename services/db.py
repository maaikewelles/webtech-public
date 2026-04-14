import sqlite3

from flask import current_app, g


def get_db() -> sqlite3.Connection:
    # aparte databaseverbinding voor gebruikers per request en inschakelen van foreign keys
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def get_books_db() -> sqlite3.Connection:
    # apart bewaren van boekendatabase, maar nog steeds per request
    if "books_db" not in g:
        g.books_db = sqlite3.connect(current_app.config["BOOKS_DATABASE"])
        g.books_db.row_factory = sqlite3.Row
    return g.books_db


def close_db(_error=None) -> None:
    for key in ("db", "books_db"):
        db = g.pop(key, None)
        if db is not None:
            db.close()


def ensure_table_columns(table_name: str, expected_columns: dict[str, str]) -> None:
    # ontbrekende kolommen toevoegen zonder bestaande tabellen opnieuw aan te maken
    db = get_db()
    existing_columns = {row["name"] for row in db.execute(f"PRAGMA table_info({table_name})").fetchall()}
    for column_name, column_definition in expected_columns.items():
        if column_name not in existing_columns:
            db.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_definition}")
