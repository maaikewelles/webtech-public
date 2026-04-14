import sqlite3

from services.books import get_book_by_id
from services.db import get_db


def list_wishlist_book_ids(user_id: int) -> list[int]:
    rows = get_db().execute(
        "SELECT book_id FROM wishlist WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,),
    ).fetchall()
    return [int(row["book_id"]) for row in rows]


def has_wishlist_book(user_id: int, book_id: int) -> bool:
    row = get_db().execute(
        "SELECT 1 FROM wishlist WHERE user_id = ? AND book_id = ?",
        (user_id, book_id),
    ).fetchone()
    return row is not None


def add_wishlist_book(user_id: int, book_id: int) -> None:
    db = get_db()
    db.execute(
        "INSERT OR IGNORE INTO wishlist (user_id, book_id) VALUES (?, ?)",
        (user_id, book_id),
    )
    db.commit()


def remove_wishlist_book(user_id: int, book_id: int) -> None:
    db = get_db()
    db.execute(
        "DELETE FROM wishlist WHERE user_id = ? AND book_id = ?",
        (user_id, book_id),
    )
    db.commit()


def list_wishlist_books(user_id: int) -> list[sqlite3.Row]:
    book_ids = list_wishlist_book_ids(user_id)
    books: list[sqlite3.Row] = []
    for book_id in book_ids:
        book = get_book_by_id(book_id)
        if book is not None:
            books.append(book)
    return books
