import sqlite3
from typing import Any

from services.db import get_books_db


BOOK_GENRES = ["Algemeen", "Financien", "Gezondheid", "Mindfulness", "Psychologie", "Relaties", "Zelfontwikkeling"]
BOOK_PRICE_FILTERS: dict[str, tuple[int | None, int | None]] = {
    "all": (None, None),
    "under-15": (None, 1499),
    "15-20": (1500, 1999),
    "20-plus": (2000, None),
}


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


def build_placeholder_books(total_books: int = 71) -> list[dict[str, str | int]]:
    """genereren van een seeded placeholder catalogus gebruikt voor de lokale boekendatabase."""
    books: list[dict[str, str | int]] = []
    for index in range(1, total_books + 1):
        genre = BOOK_GENRES[(index - 1) % len(BOOK_GENRES)]
        binding = "paperback" if index % 2 else "hardcover"
        language = "Nederlands" if index % 3 else "Engels"
        stock = 4 + (index % 7)
        delivery_days = 1 + (index % 3)
        price_cents = (12 + (index % 17)) * 100 + 95

        books.append(
            {
                "id": index,
                "title": f"Book {index}",
                "author": f"Auteur {index}",
                "isbn": f"978-1-4028-{index:05d}",
                "binding": binding,
                "language": language,
                "genre": genre,
                "summary": (
                    "Een korte beschrijving voor "
                    f"Book {index}. Dit is een korte samenvatting die de essentie van het boek neerzet. Dit klinkt lekker vaag, maar dat is ook de bedoeling. Het boek zelf is veel interessanter dan deze tekst."
                ),
                "price": format_price_cents(price_cents),
                "price_cents": price_cents,
                "delivery": f"{delivery_days}-{delivery_days + 1} werkdagen",
                "stock": stock,
            }
        )

    return books


def get_placeholder_book(book_id: int, total_books: int = 71) -> dict[str, str | int] | None:
    """teruggeven van een seeded placeholder boek op basis van id wanneer deze binnen de range van de seed valt."""
    if 1 <= book_id <= total_books:
        return build_placeholder_books(total_books)[book_id - 1]
    return None


def init_books_db() -> None:
    """aanmaken van de boektabellen aan en vul/herstel de voorbeelddata waar dat nodig is."""
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

    existing_books = db.execute("SELECT COUNT(*) AS total FROM books").fetchone()
    first_book = db.execute("SELECT title FROM books ORDER BY id LIMIT 1").fetchone()
    should_refresh_seed = first_book is not None and first_book["title"] == "Book 1"

    if existing_books is not None and existing_books["total"] == 0:
        db.executemany(
            """
            INSERT INTO books (title, author, isbn, binding, language, genre, summary, price, price_cents, delivery, stock)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    book["title"],
                    book["author"],
                    book["isbn"],
                    book["binding"],
                    book["language"],
                    book["genre"],
                    book["summary"],
                    book["price"],
                    book["price_cents"],
                    book["delivery"],
                    book["stock"],
                )
                for book in build_placeholder_books()
            ],
        )
    elif should_refresh_seed:
        db.executemany(
            """
            UPDATE books
            SET title = ?, author = ?, isbn = ?, binding = ?, language = ?, genre = ?, summary = ?, price = ?, price_cents = ?, delivery = ?, stock = ?
            WHERE id = ?
            """,
            [
                (
                    book["title"],
                    book["author"],
                    book["isbn"],
                    book["binding"],
                    book["language"],
                    book["genre"],
                    book["summary"],
                    book["price"],
                    book["price_cents"],
                    book["delivery"],
                    book["stock"],
                    book["id"],
                )
                for book in build_placeholder_books()
            ],
        )

    db.commit()


def build_book_filters(genre: str | None = None, language: str | None = None, price_filter: str | None = None) -> tuple[str, list[Any]]:
    """hier worden filterkeuzes vertaald naar SQL where-clauses met parameters."""
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
