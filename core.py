from werkzeug.security import generate_password_hash

from services.books import (
    BOOK_GENRES,
    BOOK_PRICE_FILTERS,
    build_book_filters,
    build_placeholder_books,
    count_books,
    format_price_cents,
    get_book_by_id,
    get_placeholder_book,
    init_books_db,
    list_book_genres,
    list_book_languages,
    list_books,
    normalize_book_genre,
    parse_price_text,
    search_books,
)
from services.db import close_db, ensure_table_columns, get_books_db, get_db
from services.orders import (
    create_order_for_user,
    delete_order,
    get_order_by_id,
    list_all_orders,
    list_user_orders,
    update_order_status,
)
from services.users import (
    ALLOWED_IMAGE_EXTENSIONS,
    AppUser,
    allowed_image_file,
    as_app_user,
    get_admin_settings,
    get_preferred_form,
    get_profile_image_url,
    get_user_by_email,
    get_user_by_id,
    is_valid_image_bytes,
    normalize_email,
)
from services.wishlist import (
    add_wishlist_book,
    has_wishlist_book,
    list_wishlist_book_ids,
    list_wishlist_books,
    remove_wishlist_book,
)


__all__ = [
    "ALLOWED_IMAGE_EXTENSIONS",
    "AppUser",
    "BOOK_GENRES",
    "BOOK_PRICE_FILTERS",
    "add_wishlist_book",
    "allowed_image_file",
    "as_app_user",
    "build_book_filters",
    "build_placeholder_books",
    "close_db",
    "count_books",
    "create_order_for_user",
    "delete_order",
    "ensure_table_columns",
    "format_price_cents",
    "get_admin_settings",
    "get_book_by_id",
    "get_books_db",
    "get_db",
    "get_order_by_id",
    "get_placeholder_book",
    "get_preferred_form",
    "get_profile_image_url",
    "get_user_by_email",
    "get_user_by_id",
    "has_wishlist_book",
    "init_books_db",
    "init_db",
    "is_valid_image_bytes",
    "list_all_orders",
    "list_book_genres",
    "list_book_languages",
    "list_books",
    "list_user_orders",
    "list_wishlist_book_ids",
    "list_wishlist_books",
    "normalize_book_genre",
    "normalize_email",
    "parse_price_text",
    "remove_wishlist_book",
    "search_books",
    "update_order_status",
]


def init_db() -> None:
    # het maken van tabellen, migraties en de admin-gebruiker tijdens het opstarten
    db = get_db()
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            is_admin INTEGER NOT NULL DEFAULT 0,
            profile_image TEXT,
            last_login TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS wishlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            book_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, book_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'In behandeling',
            total_cents INTEGER NOT NULL,
            customer_name TEXT NOT NULL DEFAULT '',
            customer_email TEXT NOT NULL DEFAULT '',
            address_line TEXT NOT NULL DEFAULT '',
            postal_code TEXT NOT NULL DEFAULT '',
            city TEXT NOT NULL DEFAULT '',
            phone TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            book_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            unit_price_cents INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            line_total_cents INTEGER NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
        )
        """
    )

    columns = {row["name"] for row in db.execute("PRAGMA table_info(users)").fetchall()}
    if "is_admin" not in columns:
        db.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0")
    if "profile_image" not in columns:
        db.execute("ALTER TABLE users ADD COLUMN profile_image TEXT")
    if "last_login" not in columns:
        db.execute("ALTER TABLE users ADD COLUMN last_login TIMESTAMP")

    ensure_table_columns(
        "orders",
        {
            "status": "status TEXT NOT NULL DEFAULT 'In behandeling'",
            "total_cents": "total_cents INTEGER NOT NULL DEFAULT 0",
            "customer_name": "customer_name TEXT NOT NULL DEFAULT ''",
            "customer_email": "customer_email TEXT NOT NULL DEFAULT ''",
            "address_line": "address_line TEXT NOT NULL DEFAULT ''",
            "postal_code": "postal_code TEXT NOT NULL DEFAULT ''",
            "city": "city TEXT NOT NULL DEFAULT ''",
            "phone": "phone TEXT NOT NULL DEFAULT ''",
            "notes": "notes TEXT NOT NULL DEFAULT ''",
            "created_at": "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        },
    )

    ensure_table_columns(
        "order_items",
        {
            "order_id": "order_id INTEGER",
            "book_id": "book_id INTEGER",
            "title": "title TEXT",
            "unit_price_cents": "unit_price_cents INTEGER",
            "quantity": "quantity INTEGER",
            "line_total_cents": "line_total_cents INTEGER",
        },
    )

    db.execute("CREATE INDEX IF NOT EXISTS idx_wishlist_user_id ON wishlist(user_id)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_wishlist_book_id ON wishlist(book_id)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id)")

    admin_name, admin_email, admin_password = get_admin_settings()
    existing_admin = db.execute("SELECT id FROM users WHERE email = ?", (admin_email,)).fetchone()
    if existing_admin:
        db.execute("UPDATE users SET is_admin = 1 WHERE id = ?", (existing_admin["id"],))
    else:
        db.execute(
            "INSERT INTO users (name, email, password_hash, is_admin) VALUES (?, ?, ?, 1)",
            (admin_name, admin_email, generate_password_hash(admin_password)),
        )

    db.commit()
