import secrets
from pathlib import Path

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, logout_user as flask_logout_user
from werkzeug.utils import secure_filename

from core import (
    allowed_image_file,
    delete_order,
    get_db,
    get_order_by_id,
    get_profile_image_url,
    get_user_by_id,
    is_valid_image_bytes,
    list_all_orders,
    list_user_orders,
    list_wishlist_books,
    update_order_status,
)
from services.models import User


bp = Blueprint("account", __name__)

ORDER_STATUS_OPTIONS = ["In behandeling", "Verzonden", "Afgeleverd", "Geannuleerd"]


@bp.get("/profile")
@login_required
def profile() -> str:
    message = request.args.get("message")
    user = get_user_by_id(current_user.id)
    if not user:
        flask_logout_user()
        return redirect(url_for("auth.auth"))

    return render_template(
        "profile.html",
        user=user,
        message=message,
        profile_image_url=get_profile_image_url(user["profile_image"]),
        wishlist_books=list_wishlist_books(user["id"]),
        recent_orders=list_user_orders(user["id"], limit=3),
    )


@bp.get("/orders")
@login_required
def orders() -> str:
    user = get_user_by_id(current_user.id)
    if not user:
        flask_logout_user()
        return redirect(url_for("auth.auth"))

    return render_template(
        "orders.html",
        user=user,
        orders=list_user_orders(user["id"]),
    )


@bp.get("/admin/orders")
@login_required
def admin_orders() -> str:
    user = get_user_by_id(current_user.id)
    if not user:
        flask_logout_user()
        return redirect(url_for("auth.auth"))

    if not current_user.is_admin:
        return redirect(url_for("account.orders"))

    return render_template(
        "admin_orders.html",
        user=user,
        orders=list_all_orders(),
        status_options=ORDER_STATUS_OPTIONS,
    )


@bp.post("/orders/status/<int:order_id>")
@login_required
def update_order_status_route(order_id: int):
    if not current_user.is_admin:
        return redirect(url_for("account.orders"))

    order = get_order_by_id(order_id)
    if order is None:
        flash("Bestelling niet gevonden.", "info")
        return redirect(url_for("account.admin_orders"))

    new_status = request.form.get("status", "").strip()
    if new_status not in ORDER_STATUS_OPTIONS:
        flash("Ongeldige bestelstatus.", "info")
        return redirect(url_for("account.admin_orders"))

    update_order_status(order_id, new_status)
    flash("Bestelstatus bijgewerkt.", "success")
    return redirect(url_for("account.admin_orders"))


@bp.post("/orders/delete/<int:order_id>")
@login_required
def delete_order_route(order_id: int):
    if not current_user.is_admin:
        return redirect(url_for("account.orders"))

    order = get_order_by_id(order_id)
    if order is None:
        return redirect(url_for("account.orders"))

    delete_order(order_id)
    flash("Bestelling verwijderd.", "success")
    return redirect(url_for("account.admin_orders"))


@bp.post("/profile/picture")
@login_required
def upload_profile_picture():
    # het valideren van de naam, extensie en binaire signatuur voordat de nieuwe profielfoto wordt opgeslagen
    user_id = current_user.id

    file = request.files.get("profile_picture")
    if file is None or file.filename is None or file.filename.strip() == "":
        return redirect(url_for("account.profile", message="Kies eerst een afbeelding."))

    filename = secure_filename(file.filename)
    if not filename or not allowed_image_file(filename):
        return redirect(url_for("account.profile", message="Alleen JPG, JPEG, PNG, GIF of WEBP is toegestaan."))

    ext = Path(filename).suffix.lower()
    file_bytes = file.read()
    file.stream.seek(0)
    if not is_valid_image_bytes(file_bytes, ext):
        return redirect(url_for("account.profile", message="Bestand lijkt geen geldige afbeelding."))

    new_filename = f"user_{user_id}_{secrets.token_hex(8)}{ext}"
    upload_path = Path(current_app.config["UPLOAD_FOLDER"]) / new_filename
    file.save(upload_path)

    db = get_db()
    existing = db.get(User, user_id)
    old_filename = existing.profile_image if existing else None
    if existing is not None:
        existing.profile_image = new_filename
    db.commit()

    if old_filename:
        old_path = Path(current_app.config["UPLOAD_FOLDER"]) / old_filename
        if old_path.exists() and old_path.is_file():
            old_path.unlink()

    flash("Je profielfoto is succesvol geüpdatet!", "success")
    return redirect(url_for("account.profile"))


@bp.post("/profile/picture/delete")
@login_required
def delete_profile_picture():
    user_id = current_user.id

    db = get_db()
    existing = db.get(User, user_id)
    if existing is None:
        flask_logout_user()
        return redirect(url_for("auth.auth"))

    old_filename = existing.profile_image
    existing.profile_image = None
    db.commit()

    if old_filename:
        old_path = Path(current_app.config["UPLOAD_FOLDER"]) / old_filename
        if old_path.exists() and old_path.is_file():
            old_path.unlink()

    flash("Je profielfoto is verwijderd.", "success")
    return redirect(url_for("account.profile"))
