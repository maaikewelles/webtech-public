from hashlib import sha256
from pathlib import Path
from typing import Any, TypedDict

from sqlalchemy import Select, func, inspect, or_, select, text

from services.db import get_books_db
from services.models import Book, BooksBase, SeedState


BOOK_GENRES = ["Algemeen", "Filosofie", "Financien", "Gezondheid", "Mindfulness", "Neurodiversiteit", "Psychologie", "Relaties", "Zelfontwikkeling"]
BOOK_PRICE_FILTERS: dict[str, tuple[int | None, int | None]] = {
    "all": (None, None),
    "under-15": (None, 1499),
    "15-20": (1500, 1999),
    "20-plus": (2000, None),
}

BOOKS_SEED_SQL_PATH = Path(__file__).resolve().parent.parent / "data" / "books_seed.sql"


class BookDict(TypedDict):
    id: int
    title: str
    author: str
    isbn: str
    binding: str
    language: str
    genre: str
    summary: str
    price: str
    price_cents: int
    delivery: str
    stock: int


QueryParam = str | int


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
    """het seeden van de catalogus door middel van handmatige opgestelde INSERT-statements uit het SQL-bestand uit te voeren."""
    db = get_books_db()
    if sql_script is None:
        if not BOOKS_SEED_SQL_PATH.exists():
            return 0
        sql_script = BOOKS_SEED_SQL_PATH.read_text(encoding="utf-8")

    if not sql_script.strip():
        return 0

    db.execute(text(sql_script))
    return _count_seed_rows(sql_script)


def init_books_db() -> None:
    """het aanmaken van de boektabel en deze te seeden met handmatig opgestelde INSERT-statements."""
    db = get_books_db()
    bind = db.get_bind()
    if bind is None:
        raise RuntimeError("Book database is not bound to an engine.")

    BooksBase.metadata.create_all(bind=bind)

    columns = {column["name"] for column in inspect(bind).get_columns(Book.__tablename__)}
    if "genre" not in columns:
        db.connection().exec_driver_sql("ALTER TABLE books ADD COLUMN genre TEXT NOT NULL DEFAULT 'Algemeen'")
    if "price_cents" not in columns:
        db.connection().exec_driver_sql("ALTER TABLE books ADD COLUMN price_cents INTEGER NOT NULL DEFAULT 0")
    if "stock" not in columns:
        db.connection().exec_driver_sql("ALTER TABLE books ADD COLUMN stock INTEGER NOT NULL DEFAULT 0")

    if not BOOKS_SEED_SQL_PATH.exists():
        db.commit()
        return

    sql_script = BOOKS_SEED_SQL_PATH.read_text(encoding="utf-8")
    expected_books = _count_seed_rows(sql_script)
    seed_hash = _seed_fingerprint(sql_script)
    current_books = int(db.scalar(select(func.count()).select_from(Book)) or 0)
    stored_hash = str(db.scalar(select(SeedState.value).where(SeedState.key == "books_seed_sql_sha256")) or "")

    # reseeden op een non-destructieve manier:bestaande IDs blijven gelijk en nieuwe ISBNs worden toegevoegd,
    # bestaande ISBNs worden geüpdatet via 'ON CONFLICT' in het seed-script.
    if current_books != expected_books or stored_hash != seed_hash:
        seed_books_with_insert_statements(sql_script)
        existing_seed_state = db.get(SeedState, "books_seed_sql_sha256")
        if existing_seed_state is None:
            db.add(SeedState(key="books_seed_sql_sha256", value=seed_hash))
        else:
            existing_seed_state.value = seed_hash

    db.commit()


def build_book_filters(genre: str | None = None, language: str | None = None, price_filter: str | None = None) -> tuple[str, list[QueryParam]]:
    """hier worden filterkeuzes omgezet naar SQL where-clauses met parameters."""
    clauses: list[str] = []
    params: list[QueryParam] = []

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


def _apply_book_filters(statement: Select[Any], genre: str | None, language: str | None, price_filter: str | None) -> Select[Any]:
    if genre and genre != "all":
        statement = statement.where(Book.genre == genre)

    if language and language != "all":
        statement = statement.where(Book.language == language)

    normalized_price_filter = price_filter if price_filter in BOOK_PRICE_FILTERS else "all"
    minimum_price, maximum_price = BOOK_PRICE_FILTERS[normalized_price_filter]
    if minimum_price is not None:
        statement = statement.where(Book.price_cents >= minimum_price)
    if maximum_price is not None:
        statement = statement.where(Book.price_cents <= maximum_price)

    return statement


def _book_to_dict(book: Book) -> BookDict:
    return {
        "id": book.id,
        "title": book.title,
        "author": book.author,
        "isbn": book.isbn,
        "binding": book.binding,
        "language": book.language,
        "genre": book.genre,
        "summary": book.summary,
        "price": book.price,
        "price_cents": book.price_cents,
        "delivery": book.delivery,
        "stock": book.stock,
    }


def count_books(genre: str | None = None, language: str | None = None, price_filter: str | None = None) -> int:
    """het tellen van boeken na het toepassen van geselecteerde filters."""
    session = get_books_db()
    statement = select(func.count()).select_from(Book)
    statement = _apply_book_filters(statement, genre, language, price_filter)
    return int(session.scalar(statement) or 0)


def list_books(
    limit: int | None = None,
    offset: int = 0,
    genre: str | None = None,
    language: str | None = None,
    price_filter: str | None = None,
) -> list[Any]:
    """teruggeven van boeken voor de overzichtapagina met optionele filters en paginering."""
    session = get_books_db()
    statement = select(Book).order_by(Book.id)
    statement = _apply_book_filters(statement, genre, language, price_filter)
    if limit is not None:
        statement = statement.limit(limit).offset(offset)

    return [_book_to_dict(book) for book in session.scalars(statement).all()]


def search_books(query_text: str, limit: int = 50) -> list[BookDict]:
    """zoeken in de boekencatalogus over de hoofdtekstvelden."""
    normalized_query = query_text.strip()
    if not normalized_query:
        return []

    search_term = f"%{normalized_query}%"
    session = get_books_db()
    statement = (
        select(Book)
        .where(
            or_(
                Book.title.like(search_term),
                Book.author.like(search_term),
                Book.isbn.like(search_term),
                Book.genre.like(search_term),
                Book.language.like(search_term),
                Book.summary.like(search_term),
            )
        )
        .order_by(Book.id)
        .limit(limit)
    )
    return [_book_to_dict(book) for book in session.scalars(statement).all()]


def list_book_genres() -> list[str]:
    """teruggeven van de verschillende genres die momenteel beschikbaar zijn in de boekendatabase."""
    session = get_books_db()
    statement = select(Book.genre).where(Book.genre.is_not(None), Book.genre != "").distinct().order_by(Book.genre)
    return [str(genre) for genre in session.scalars(statement).all() if genre]


def list_book_languages() -> list[str]:
    """teruggeven van de verschillende talen die momenteel beschikbaar zijn in de boekendatabase."""
    session = get_books_db()
    statement = select(Book.language).where(Book.language.is_not(None), Book.language != "").distinct().order_by(Book.language)
    return [str(language) for language in session.scalars(statement).all() if language]


def get_book_by_id(book_id: int) -> BookDict | None:
    """fetchen van een boek op basis van id."""
    book = get_books_db().get(Book, book_id)
    return _book_to_dict(book) if book is not None else None