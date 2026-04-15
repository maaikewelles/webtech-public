import sqlite3
from hashlib import sha256
from pathlib import Path
from typing import Any

from services.db import get_books_db


BOOK_GENRES = ["Algemeen", "Filosofie", "Financien", "Gezondheid", "Mindfulness", "Neurodiversiteit", "Psychologie", "Relaties", "Zelfontwikkeling"]
BOOK_PRICE_FILTERS: dict[str, tuple[int | None, int | None]] = {
    "all": (None, None),
    "under-15": (None, 1499),
    "15-20": (1500, 1999),
    "20-plus": (2000, None),
}

BOOKS_SEED_SQL_PATH = Path(__file__).resolve().parent.parent / "data" / "books_seed.sql"


def format_price_cents(price_cents: int) -> str:
    """formatteren van prijs in centen naar de EUR notatie die in de webshop wordt gehanteerd."""
    euros, cents = divmod(price_cents, 100)
    return f"EUR {euros},{cents:02d}"


def parse_price_text(price_text: str) -> int:
    """geformatteerde prijs terug omzetten naar centen."""
    cleaned_price = price_text.upper().replace("EUR", "").strip().replace(".", "")
    euros_text, _, cents_text = cleaned_price.partition(",")
    euros = int(euros_text or "0")
    cents = int((cents_text + "00")[:2]) if cents_text else 0
    return euros * 100 + cents


def normalize_book_genre(genre: str | None) -> str:
    """teruggeven van een "veilig" standaardgenre wanneer de bronwaarde leeg is."""
    if not genre:
        return "Algemeen"

    normalized_genre = genre.strip()
    return normalized_genre if normalized_genre else "Algemeen"


def _count_seed_rows(sql_script: str) -> int:
    return sum(1 for line in sql_script.splitlines() if line.lstrip().startswith("('"))


def _seed_fingerprint(sql_script: str) -> str:
    return sha256(sql_script.encode("utf-8")).hexdigest()


def seed_books_with_insert_statements(sql_script: str | None = None) -> int:
    """het seeden van de catalogus door middel van handmatige INSERT-statements uit het SQL-bestand uit te voeren."""
    db = get_books_db()
    if sql_script is None:
        if not BOOKS_SEED_SQL_PATH.exists():
            return 0
        sql_script = BOOKS_SEED_SQL_PATH.read_text(encoding="utf-8")

    if not sql_script.strip():
        return 0

    db.executescript(sql_script)
    return _count_seed_rows(sql_script)


def init_books_db() -> None:
    """het aanmaken van de boektabel en deze te seeden met handmatige INSERT-statements."""
    db = get_books_db()
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            isbn TEXT NOT NULL UNIQUE,
            binding TEXT NOT NULL,
            language TEXT NOT NULL,
            genre TEXT NOT NULL DEFAULT 'Algemeen',
            summary TEXT NOT NULL,
            price TEXT NOT NULL,
            price_cents INTEGER NOT NULL DEFAULT 0,
            delivery TEXT NOT NULL,
            stock INTEGER NOT NULL DEFAULT 0
        )
        """
    )

    columns = {row["name"] for row in db.execute("PRAGMA table_info(books)").fetchall()}
    if "genre" not in columns:
        db.execute("ALTER TABLE books ADD COLUMN genre TEXT NOT NULL DEFAULT 'Algemeen'")
    if "price_cents" not in columns:
        db.execute("ALTER TABLE books ADD COLUMN price_cents INTEGER NOT NULL DEFAULT 0")
    if "stock" not in columns:
        db.execute("ALTER TABLE books ADD COLUMN stock INTEGER NOT NULL DEFAULT 0")

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS seed_state (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )

    if not BOOKS_SEED_SQL_PATH.exists():
        db.commit()
        return

    sql_script = BOOKS_SEED_SQL_PATH.read_text(encoding="utf-8")
    expected_books = _count_seed_rows(sql_script)
    seed_hash = _seed_fingerprint(sql_script)
    current_books_row = db.execute("SELECT COUNT(*) AS total FROM books").fetchone()
    current_books = int(current_books_row["total"]) if current_books_row is not None else 0
    stored_hash_row = db.execute(
        "SELECT value FROM seed_state WHERE key = ?",
        ("books_seed_sql_sha256",),
    ).fetchone()
    stored_hash = str(stored_hash_row["value"]) if stored_hash_row is not None else ""

    # Reseed als inhoud van books_seed.sql is gewijzigd of aantallen afwijken.
    if current_books != expected_books or stored_hash != seed_hash:
        db.execute("DELETE FROM books")
        seed_books_with_insert_statements(sql_script)
        db.execute(
            """
            INSERT INTO seed_state (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            ("books_seed_sql_sha256", seed_hash),
        )

    db.commit()


def build_book_filters(genre: str | None = None, language: str | None = None, price_filter: str | None = None) -> tuple[str, list[Any]]:
    """hier worden filterkeuzes omgezet naar SQL where-clauses met parameters."""
    clauses: list[str] = []
    params: list[Any] = []

    if genre and genre != "all":
        clauses.append("genre = ?")
        params.append(genre)

    if language and language != "all":
        clauses.append("language = ?")
        params.append(language)

    normalized_price_filter = price_filter if price_filter in BOOK_PRICE_FILTERS else "all"
    minimum_price, maximum_price = BOOK_PRICE_FILTERS[normalized_price_filter]
    if minimum_price is not None:
        clauses.append("price_cents >= ?")
        params.append(minimum_price)
    if maximum_price is not None:
        clauses.append("price_cents <= ?")
        params.append(maximum_price)

    if not clauses:
        return "", params

    return " WHERE " + " AND ".join(clauses), params


def count_books(genre: str | None = None, language: str | None = None, price_filter: str | None = None) -> int:
    """het tellen van boeken na het toepassen van geselecteerde filters."""
    where_clause, params = build_book_filters(genre, language, price_filter)
    row = get_books_db().execute(f"SELECT COUNT(*) AS total FROM books{where_clause}", params).fetchone()
    if row is None:
        return 0
    return int(row["total"])


def list_books(
    limit: int | None = None,
    offset: int = 0,
    genre: str | None = None,
    language: str | None = None,
    price_filter: str | None = None,
) -> list[sqlite3.Row]:
    """teruggeven van boeken voor de overzichtapagina met optionele filters en paginering."""
    where_clause, params = build_book_filters(genre, language, price_filter)
    query = (
        "SELECT id, title, author, isbn, binding, language, genre, summary, price, price_cents, delivery, stock "
        f"FROM books{where_clause} ORDER BY id"
    )

    if limit is not None:
        query += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])

    rows = get_books_db().execute(query, params).fetchall()
    return list(rows)


def search_books(query_text: str, limit: int = 50) -> list[sqlite3.Row]:
    """zoeken in de boekencatalogus over de hoofdtekstvelden."""
    normalized_query = query_text.strip()
    if not normalized_query:
        return []

    search_term = f"%{normalized_query}%"
    rows = get_books_db().execute(
        """
        SELECT id, title, author, isbn, binding, language, genre, summary, price, price_cents, delivery, stock
        FROM books
        WHERE title LIKE ?
           OR author LIKE ?
           OR isbn LIKE ?
           OR genre LIKE ?
           OR language LIKE ?
           OR summary LIKE ?
        ORDER BY id
        LIMIT ?
        """,
        [search_term, search_term, search_term, search_term, search_term, search_term, limit],
    ).fetchall()
    return list(rows)


def list_book_genres() -> list[str]:
    """teruggeven van de verschillende genres die momenteel beschikbaar zijn in de boekendatabase."""
    rows = get_books_db().execute(
        "SELECT DISTINCT genre FROM books WHERE genre IS NOT NULL AND genre != '' ORDER BY genre"
    ).fetchall()
    return [row["genre"] for row in rows if row["genre"]]


def list_book_languages() -> list[str]:
    """teruggeven van de verschillende talen die momenteel beschikbaar zijn in de boekendatabase."""
    rows = get_books_db().execute(
        "SELECT DISTINCT language FROM books WHERE language IS NOT NULL AND language != '' ORDER BY language"
    ).fetchall()
    return [row["language"] for row in rows if row["language"]]


def get_book_by_id(book_id: int) -> sqlite3.Row | None:
    """fetchen van een boek op basis van id."""
    return get_books_db().execute(
        "SELECT id, title, author, isbn, binding, language, genre, summary, price, price_cents, delivery, stock FROM books WHERE id = ?",
        (book_id,),
    ).fetchone()
