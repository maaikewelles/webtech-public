import os
import sqlite3
from pathlib import Path

from flask import current_app, url_for
from flask_login import UserMixin

from services.db import get_db


ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


class AppUser(UserMixin):
    """flask-login compatible user wrapper rond een rij in de database."""

    def __init__(self, row: sqlite3.Row):
        self.id = int(row["id"])
        self.name = row["name"]
        self.email = row["email"]
        self.is_admin = bool(row["is_admin"])

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


def get_user_by_id(user_id: int) -> sqlite3.Row | None:
    """een user row ophalen op basis van id."""
    return get_db().execute(
        "SELECT id, name, email, is_admin, profile_image, created_at FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()


def get_user_by_email(email: str) -> sqlite3.Row | None:
    """ophalen van de authenticatievelden voor één gebruiker op basis van email."""
    return get_db().execute(
        "SELECT id, name, email, password_hash, is_admin, last_login FROM users WHERE email = ?",
        (email,),
    ).fetchone()


def as_app_user(user: sqlite3.Row | None) -> AppUser | None:
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
