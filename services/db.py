from flask import current_app, g
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


def _create_sqlite_engine(database_path: str) -> Engine:
    return create_engine(f"sqlite+pysqlite:///{database_path}", future=True)


def _get_engine(config_key: str, g_key: str) -> Engine:
    if not hasattr(g, g_key):
        setattr(g, g_key, _create_sqlite_engine(current_app.config[config_key]))
    return getattr(g, g_key)


def _get_session(engine_key: str, session_key: str, config_key: str) -> Session:
    if not hasattr(g, session_key):
        engine = _get_engine(config_key, engine_key)
        session_factory = sessionmaker(bind=engine, future=True, expire_on_commit=False)
        setattr(g, session_key, session_factory())
        getattr(g, session_key).connection().exec_driver_sql("PRAGMA foreign_keys = ON")
    return getattr(g, session_key)


def get_db() -> Session:
    """een aparte SQLAlchemy-sessie voor gebruikers per request met ingeschakelde foreign keys."""
    return _get_session("users_engine", "users_session", "DATABASE")


def get_books_db() -> Session:
    """een aparte SQLAlchemy-sessie voor de boekendatabase per request."""
    return _get_session("books_engine", "books_session", "BOOKS_DATABASE")


def close_db(_error=None) -> None:
    """het sluiten van open databaseverbindingen en engines aan het einde van het request."""
    for key in ("users_session", "books_session"):
        db = g.pop(key, None)
        if db is not None:
            db.close()

    for key in ("users_engine", "books_engine"):
        engine = g.pop(key, None)
        if engine is not None:
            engine.dispose()


def ensure_table_columns(table_name: str, expected_columns: dict[str, str]) -> None:
    """hier worden ontbrekende kolommen toegevoegd zonder bestaande tabellen opnieuw aan te maken."""
    db = get_db()
    existing_columns = {
        row["name"]
        for row in db.connection().exec_driver_sql(f"PRAGMA table_info({table_name})").mappings().all()
    }
    for column_name, column_definition in expected_columns.items():
        if column_name not in existing_columns:
            db.connection().exec_driver_sql(f"ALTER TABLE {table_name} ADD COLUMN {column_definition}")
