from urllib.parse import urlparse

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required

from core import create_order_for_user, format_price_cents, get_book_by_id, parse_price_text


bp = Blueprint("cart", __name__)

CART_SESSION_KEY = "cart"


def get_cart() -> dict[str, int]:
    raw_cart = session.get(CART_SESSION_KEY, {})
    if not isinstance(raw_cart, dict):
        return {}

    normalized_cart: dict[str, int] = {}
    dirty = False
    for raw_book_id, raw_quantity in raw_cart.items():
        try:
            book_id = int(raw_book_id)
            quantity = int(raw_quantity)
        except (TypeError, ValueError):
            dirty = True
            continue

        if quantity < 1:
            dirty = True
            continue

        normalized_cart[str(book_id)] = quantity

    if dirty or normalized_cart != raw_cart:
        session[CART_SESSION_KEY] = normalized_cart
        session.modified = True

    return normalized_cart


def get_cart_item_count() -> int:
    return sum(get_cart().values())


def save_cart(cart: dict[str, int]) -> None:
    session[CART_SESSION_KEY] = cart
    session.modified = True


def safe_redirect(default_target: str) -> str:
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


def update_cart_quantity(book_id: int, quantity: int) -> None:
    cart = get_cart()
    key = str(book_id)
    if quantity < 1:
        cart.pop(key, None)
    else:
        cart[key] = quantity
    save_cart(cart)


def build_cart_items() -> tuple[list[dict[str, object]], int, int]:
    cart = get_cart()
    cart_items: list[dict[str, object]] = []
    total_items = 0
    subtotal_cents = 0
    removed_items = False

    for raw_book_id, quantity in cart.items():
        book = get_book_by_id(int(raw_book_id))
        if book is None:
            removed_items = True
            continue

        unit_price_cents = parse_price_text(book["price"])
        line_total_cents = unit_price_cents * quantity
        cart_items.append(
            {
                "book": book,
                "quantity": quantity,
                "unit_price": book["price"],
                "unit_price_cents": unit_price_cents,
                "line_total": format_price_cents(line_total_cents),
                "line_total_cents": line_total_cents,
            }
        )
        total_items += quantity
        subtotal_cents += line_total_cents

    if removed_items:
        save_cart({str(item["book"]["id"]): int(item["quantity"]) for item in cart_items})

    return cart_items, total_items, subtotal_cents


@bp.get("/cart")
def cart_page() -> str:
    cart_items, total_items, subtotal_cents = build_cart_items()
    return render_template(
        "cart.html",
        cart_items=cart_items,
        total_items=total_items,
        subtotal=format_price_cents(subtotal_cents),
        body_class="cart-page",
    )


@bp.post("/cart/add/<int:book_id>")
def cart_add(book_id: int):
    book = get_book_by_id(book_id)
    if book is None:
        abort(404)

    try:
        quantity = int(request.form.get("quantity", "1"))
    except ValueError:
        quantity = 1

    quantity = max(1, min(quantity, 99))
    update_cart_quantity(book_id, get_cart().get(str(book_id), 0) + quantity)
    flash(f"Je hebt {book['title']} toegevoegd aan je mandje!", "success")
    return redirect(safe_redirect(url_for("cart.cart_page")))


@bp.post("/cart/update/<int:book_id>")
def cart_update(book_id: int):
    if get_book_by_id(book_id) is None:
        abort(404)

    try:
        quantity = int(request.form.get("quantity", "1"))
    except ValueError:
        quantity = 1

    update_cart_quantity(book_id, max(0, min(quantity, 99)))
    is_auto_update = request.form.get("auto_update") == "1"
    if not is_auto_update:
        flash("Winkelmandje bijgewerkt.", "success")
    return redirect(url_for("cart.cart_page"))


@bp.post("/cart/remove/<int:book_id>")
def cart_remove(book_id: int):
    book = get_book_by_id(book_id)
    if book is None:
        abort(404)

    update_cart_quantity(book_id, 0)
    flash(f"Je hebt {book['title']} verwijderd uit je mandje!", "success")
    return redirect(url_for("cart.cart_page"))


@bp.post("/cart/clear")
def cart_clear():
    session.pop(CART_SESSION_KEY, None)
    session.modified = True
    flash("Winkelmandje geleegd.", "success")
    return redirect(url_for("cart.cart_page"))


@bp.route("/cart/checkout", methods=["GET", "POST"])
@login_required
def cart_checkout():
    cart_items, total_items, subtotal_cents = build_cart_items()
    if not cart_items:
        flash("Je winkelmandje is leeg.", "info")
        return redirect(url_for("cart.cart_page"))

    checkout_defaults = {
        "customer_name": current_user.name,
        "customer_email": current_user.email,
        "address_line": "",
        "postal_code": "",
        "city": "",
        "phone": "",
        "notes": "",
    }

    if request.method == "GET":
        return render_template(
            "checkout.html",
            cart_items=cart_items,
            total_items=total_items,
            subtotal=format_price_cents(subtotal_cents),
            form_data=checkout_defaults,
            errors={},
            body_class="cart-page checkout-page",
        )

    form_data = {
        "customer_name": request.form.get("customer_name", "").strip(),
        "customer_email": request.form.get("customer_email", "").strip(),
        "address_line": request.form.get("address_line", "").strip(),
        "postal_code": request.form.get("postal_code", "").strip(),
        "city": request.form.get("city", "").strip(),
        "phone": request.form.get("phone", "").strip(),
        "notes": request.form.get("notes", "").strip(),
    }

    errors: dict[str, str] = {}
    required_fields = {
        "customer_name": "Vul je naam in.",
        "customer_email": "Vul je e-mailadres in.",
        "address_line": "Vul je adres in.",
        "postal_code": "Vul je postcode in.",
        "city": "Vul je woonplaats in.",
    }

    for field_name, error_message in required_fields.items():
        if not form_data[field_name]:
            errors[field_name] = error_message

    if form_data["customer_email"] and "@" not in form_data["customer_email"]:
        errors["customer_email"] = "Vul een geldig e-mailadres in."

    if errors:
        return render_template(
            "checkout.html",
            cart_items=cart_items,
            total_items=total_items,
            subtotal=format_price_cents(subtotal_cents),
            form_data=form_data,
            errors=errors,
            body_class="cart-page checkout-page",
        )

    create_order_for_user(current_user.id, cart_items, subtotal_cents, form_data)
    session.pop(CART_SESSION_KEY, None)
    session.modified = True

    flash("Je bestelling is geplaatst.", "success")
    return redirect(url_for("account.orders"))
