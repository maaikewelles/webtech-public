import os
from pathlib import Path
from typing import Mapping, TypedDict

from flask import current_app, url_for
from flask_login import UserMixin
from sqlalchemy import select
from werkzeug.security import generate_password_hash

from services.db import ensure_table_columns, get_db
from services.models import User, UsersBase


ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


class UserPublicDict(TypedDict):
    id: int
    name: str
    email: str
    is_admin: int
    profile_image: str | None
    created_at: str


class UserAuthDict(TypedDict):
    id: int
    name: str
    email: str
    password_hash: str
    is_admin: int
    last_login: str | None


class AppUser(UserMixin):
    """flask-login compatible user wrapper rond een rij in de database."""

    def __init__(self, row: UserPublicDict | UserAuthDict | User):
        self.id = int(_row_value(row, "id"))
        self.name = str(_row_value(row, "name"))
        self.email = str(_row_value(row, "email"))
        self.is_admin = bool(_row_value(row, "is_admin"))

    def get_id(self) -> str:
        """return van string id verwacht door flask-login."""
        return str(self.id)


def normalize_email(email: str) -> str:
    """normaliseren van een emailadres voor vergelijking en opslag."""
    return email.strip().lower()


def get_preferred_form(form_value: str | None) -> str:
    """teruggeven van het actieve authenticatieformulier, standaard login."""
    if form_value in {"login", "register"}:
        return form_value
    return "login"


def get_admin_settings() -> tuple[str, str, str]:
    """adminaccount omgevingsvariabelen uitlezen."""
    admin_name = os.environ.get("ADMIN_NAME", "Admin").strip() or "Admin"
    admin_email = normalize_email(os.environ.get("ADMIN_EMAIL", "admin@hoofdzaken.nl"))
    admin_password = os.environ.get("ADMIN_PASSWORD", "Admin123!")
    return admin_name, admin_email, admin_password


def allowed_image_file(filename: str) -> bool:
    """controle of een bestand een toegestane image-extensie heeft."""
    return Path(filename).suffix.lower() in ALLOWED_IMAGE_EXTENSIONS


def is_valid_image_bytes(data: bytes, ext: str) -> bool:
    """hier wordt de bestandsheader gecontroleerd in plaats van alleen de extensie."""
    ext = ext.lower()
    if ext == ".png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    if ext in {".jpg", ".jpeg"}:
        return data.startswith(b"\xff\xd8")
    if ext == ".gif":
        return data.startswith(b"GIF87a") or data.startswith(b"GIF89a")
    if ext == ".webp":
        return len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP"
    return False


def init_users_db() -> None:
    """het aanmaken van de gebruikers-, bestelling- en wishlisttabellen met behulp van SQLAlchemy."""
    db = get_db()
    bind = db.get_bind()
    if bind is None:
        raise RuntimeError("Users database is not bound to an engine.")

    UsersBase.metadata.create_all(bind=bind)

    ensure_table_columns(
        "users",
        {
            "is_admin": "is_admin INTEGER NOT NULL DEFAULT 0",
            "profile_image": "profile_image TEXT",
            "last_login": "last_login TEXT",
            "created_at": "created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP",
        },
    )
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
            "created_at": "created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP",
        },
    )
    ensure_table_columns(
        "order_items",
        {
            "order_id": "order_id INTEGER NOT NULL",
            "book_id": "book_id INTEGER NOT NULL",
            "title": "title TEXT NOT NULL",
            "unit_price_cents": "unit_price_cents INTEGER NOT NULL",
            "quantity": "quantity INTEGER NOT NULL",
            "line_total_cents": "line_total_cents INTEGER NOT NULL",
        },
    )

    db.connection().exec_driver_sql("CREATE INDEX IF NOT EXISTS idx_wishlist_user_id ON wishlist(user_id)")
    db.connection().exec_driver_sql("CREATE INDEX IF NOT EXISTS idx_wishlist_book_id ON wishlist(book_id)")
    db.connection().exec_driver_sql("CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id)")
    db.connection().exec_driver_sql("CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id)")

    admin_name, admin_email, admin_password = get_admin_settings()
    existing_admin = db.scalar(select(User).where(User.email == admin_email))
    if existing_admin is not None:
        existing_admin.is_admin = 1
    else:
        db.add(User(name=admin_name, email=admin_email, password_hash=generate_password_hash(admin_password), is_admin=1))

    db.commit()


def get_user_by_id(user_id: int) -> UserPublicDict | None:
    """een user row ophalen op basis van id."""
    user = get_db().get(User, user_id)
    return _user_to_dict(user) if user is not None else None


def get_user_by_email(email: str) -> UserAuthDict | None:
    """ophalen van de authenticatievelden voor één gebruiker op basis van email."""
    user = get_db().scalar(select(User).where(User.email == email))
    return _user_to_auth_dict(user) if user is not None else None


def as_app_user(user: UserPublicDict | UserAuthDict | User | None) -> AppUser | None:
    """wrappen van een user row in de flask-login user class wanneer deze bestaat."""
    if user is None:
        return None
    return AppUser(user)


def get_profile_image_url(profile_image_filename: str | None) -> str:
    """terugvallen op de standaardafbeelding als een geüploade profielfoto ontbreekt."""
    default_url = url_for("static", filename="default_profile.png")
    if not profile_image_filename:
        return default_url

    candidate_path = Path(current_app.config["UPLOAD_FOLDER"]) / profile_image_filename
    if candidate_path.exists() and candidate_path.is_file():
        return url_for("static", filename=f"uploads/{profile_image_filename}")
    return default_url


def _row_value(row: Mapping[str, object] | User, key: str) -> object:
    if hasattr(row, key):
        return getattr(row, key)
    return row[key]


def _user_to_dict(user: User) -> UserPublicDict:
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "is_admin": user.is_admin,
        "profile_image": user.profile_image,
        "created_at": user.created_at,
    }


def _user_to_auth_dict(user: User) -> UserAuthDict:
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "password_hash": user.password_hash,
        "is_admin": user.is_admin,
        "last_login": user.last_login,
    }