from urllib.parse import urlparse

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from core import (
    add_wishlist_book,
    count_books,
    get_book_by_id,
    has_wishlist_book,
    list_book_genres,
    list_book_languages,
    list_books,
    list_wishlist_book_ids,
    remove_wishlist_book,
    search_books,
)


bp = Blueprint("shop", __name__)


def safe_redirect(default_target: str) -> str:
    # alleen toestaan van interne redirects, zodat gebruikers niet per ongeluk onverwachts naar een externe site gaan
    target = request.form.get("next") or request.args.get("next")
    if not target:
        return default_target

    parsed_target = urlparse(target)
    if parsed_target.scheme and parsed_target.netloc:
        if parsed_target.netloc != request.host:
            return default_target
        return parsed_target.path + (f"?{parsed_target.query}" if parsed_target.query else "")

    if target.startswith("/"):
        return target

    return default_target


@bp.get("/shop")
def shop() -> str:
    # eerst valideren van filters en paginering, daarna pas het opbouwen van de query en weergavegegevens
    per_page = 15
    available_genres = list_book_genres()
    available_languages = list_book_languages()
    wishlist_book_ids: set[int] = set()

    if current_user.is_authenticated:
        wishlist_book_ids = set(list_wishlist_book_ids(current_user.id))

    selected_genre = request.args.get("genre", "all")
    if selected_genre != "all" and selected_genre not in available_genres:
        selected_genre = "all"

    selected_language = request.args.get("language", "all")
    if selected_language != "all" and selected_language not in available_languages:
        selected_language = "all"

    selected_price = request.args.get("price", "all")
    if selected_price not in {"all", "under-15", "15-20", "20-plus"}:
        selected_price = "all"

    try:
        page = int(request.args.get("page", "1"))
    except ValueError:
        page = 1

    total_books = count_books(selected_genre, selected_language, selected_price)
    total_pages = max((total_books + per_page - 1) // per_page, 1)
    page = max(1, min(page, total_pages))

    start_index = (page - 1) * per_page
    visible_books = list_books(
        limit=per_page,
        offset=start_index,
        genre=selected_genre,
        language=selected_language,
        price_filter=selected_price,
    )

    pager_items: list[dict[str, object]] = []
    if total_pages > 1 and page > 1:
        pager_items.append({"type": "arrow", "page": page - 1, "label": "<"})

    pager_items.append({"type": "page", "page": page, "label": str(page), "current": True})

    if total_pages > 1 and page < total_pages:
        pager_items.append({"type": "arrow", "page": page + 1, "label": ">"})

    return render_template(
        "shop.html",
        books=visible_books,
        page=page,
        total_pages=total_pages,
        pager_items=pager_items,
        available_genres=available_genres,
        available_languages=available_languages,
        selected_genre=selected_genre,
        selected_language=selected_language,
        selected_price=selected_price,
        wishlist_book_ids=wishlist_book_ids,
        body_class="shop-page",
    )


@bp.get("/gifts")
def gifts() -> str:
    curated_rows = [
        {
            "prompt": "Inspiratie voor degene die moeite heeft met zich houden aan nieuwjaarsresoluties...",
            "book_titles": ["Atomic Habits", "Financial Selfcare", "Opgeruimd!"],
        },
        {
            "prompt": "Inspiratie voor de romanticus die beter wil leren luisteren...",
            "book_titles": ["Houd me vast", "All About Love", "De 5 talen van de liefde"],
        },
        {
            "prompt": "Inspiratie voor degene die bezig is met persoonlijke groei en zelfinzicht...",
            "book_titles": ["Own the Room", "Wees eens lief voor jezelf", "The Let Them Theory"],
        },
        {
            "prompt": "Inspiratie voor degene die wil leren over neurodiversiteit...",
            "book_titles": ["Maar je ziet er helemaal niet autistisch uit", "Druks", "Anders gaat ook"],
        },
        {
            "prompt": "Inspiratie voor degene wiens innerlijke filosoof steeds meer naar boven komt...",
            "book_titles": ["Socrates op sneakers", "Tao: De levende religie van China", "Meditations"],
        },
    ]
    gift_rows: list[dict[str, object]] = []

    books_by_title = {book["title"]: book for book in list_books(limit=500)}

    # alleen opnemen van titels die ook echt in de daadwerkelijk catalogus staan.
    for row in curated_rows:
        row_books = [
            books_by_title[title]
            for title in row["book_titles"]
            if title in books_by_title
        ]

        gift_rows.append({"prompt": row["prompt"], "books": row_books})

    return render_template("gifts.html", gift_rows=gift_rows, body_class="gifts-page")


@bp.get("/search")
def search_page() -> str:
    query_text = request.args.get("q", "").strip()
    results = search_books(query_text) if query_text else []
    return render_template("search.html", query_text=query_text, results=results)


@bp.get("/shop/product/<int:book_id>")
def product_page(book_id: int) -> str:
    book = get_book_by_id(book_id)
    if book is None:
        abort(404)
    is_wishlist_book = current_user.is_authenticated and has_wishlist_book(current_user.id, book_id)
    return render_template("product.html", book=book, is_wishlist_book=is_wishlist_book, body_class="shop-page")


@bp.post("/wishlist/toggle/<int:book_id>")
@login_required
def wishlist_toggle(book_id: int):
    # wisselen van de wishlist-status
    book = get_book_by_id(book_id)
    if book is None:
        abort(404)

    if has_wishlist_book(current_user.id, book_id):
        remove_wishlist_book(current_user.id, book_id)
        flash(f"Je hebt {book['title']} verwijderd uit je wishlist!", "success")
    else:
        add_wishlist_book(current_user.id, book_id)
        flash(f"Je hebt {book['title']} toegevoegd aan je wishlist!", "success")

    return redirect(safe_redirect(url_for("shop.shop")))
