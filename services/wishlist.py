from sqlalchemy import delete, select

from services.books import BookDict, get_book_by_id
from services.db import get_db
from services.models import WishlistItem


def list_wishlist_book_ids(user_id: int) -> list[int]:
    db = get_db()
    statement = select(WishlistItem.book_id).where(WishlistItem.user_id == user_id).order_by(WishlistItem.created_at.desc())
    return [int(book_id) for book_id in db.scalars(statement).all()]


def has_wishlist_book(user_id: int, book_id: int) -> bool:
    db = get_db()
    return db.scalar(select(WishlistItem.id).where(WishlistItem.user_id == user_id, WishlistItem.book_id == book_id)) is not None


def add_wishlist_book(user_id: int, book_id: int) -> None:
    db = get_db()
    if not has_wishlist_book(user_id, book_id):
        db.add(WishlistItem(user_id=user_id, book_id=book_id))
    db.commit()


def remove_wishlist_book(user_id: int, book_id: int) -> None:
    db = get_db()
    db.execute(delete(WishlistItem).where(WishlistItem.user_id == user_id, WishlistItem.book_id == book_id))
    db.commit()


def list_wishlist_books(user_id: int) -> list[BookDict]:
    book_ids = list_wishlist_book_ids(user_id)
    books: list[BookDict] = []
    for book_id in book_ids:
        book = get_book_by_id(book_id)
        if book is not None:
            books.append(book)
    return books