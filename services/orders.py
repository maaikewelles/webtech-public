import sqlite3
from typing import Any

from services.books import format_price_cents
from services.db import get_db


def create_order_for_user(
    user_id: int,
    cart_items: list[dict[str, Any]],
    total_cents: int,
    checkout_details: dict[str, str],
) -> int:
    """eerst orderknop wegschrijven en daarna losse orderregels toevoegen."""
    db = get_db()
    cursor = db.execute(
        """
        INSERT INTO orders (
            user_id,
            status,
            total_cents,
            customer_name,
            customer_email,
            address_line,
            postal_code,
            city,
            phone,
            notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            "In behandeling",
            total_cents,
            checkout_details.get("customer_name", ""),
            checkout_details.get("customer_email", ""),
            checkout_details.get("address_line", ""),
            checkout_details.get("postal_code", ""),
            checkout_details.get("city", ""),
            checkout_details.get("phone", ""),
            checkout_details.get("notes", ""),
        ),
    )
    order_id = int(cursor.lastrowid)

    db.executemany(
        """
        INSERT INTO order_items (order_id, book_id, title, unit_price_cents, quantity, line_total_cents)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            (
                order_id,
                int(item["book"]["id"]),
                str(item["book"]["title"]),
                int(item["unit_price_cents"]),
                int(item["quantity"]),
                int(item["line_total_cents"]),
            )
            for item in cart_items
        ],
    )
    db.commit()
    return order_id


def list_user_orders(user_id: int, limit: int | None = None) -> list[dict[str, Any]]:
    """combineren van order- en itemregels tot compacte cards voor de accountweergave."""
    query = (
        "SELECT id, user_id, status, total_cents, created_at FROM orders "
        "WHERE user_id = ? ORDER BY id DESC"
    )
    params: list[Any] = [user_id]

    if limit is not None:
        query += " LIMIT ?"
        params.append(limit)

    order_rows = get_db().execute(query, params).fetchall()
    if not order_rows:
        return []

    order_ids = [int(row["id"]) for row in order_rows]
    placeholders = ",".join(["?"] * len(order_ids))
    item_rows = get_db().execute(
        """
        SELECT order_id, book_id, title, quantity
        FROM order_items
        WHERE order_id IN (
        """
        + placeholders
        + ") ORDER BY id",
        order_ids,
    ).fetchall()

    items_by_order: dict[int, list[dict[str, Any]]] = {order_id: [] for order_id in order_ids}
    for row in item_rows:
        title = str(row["title"])
        quantity = int(row["quantity"])
        label = f"{title} x{quantity}" if quantity > 1 else title
        items_by_order[int(row["order_id"])].append(
            {
                "title": label,
                "book_id": int(row["book_id"]),
            }
        )

    orders: list[dict[str, Any]] = []
    for row in order_rows:
        order_id = int(row["id"])
        created_at = str(row["created_at"])
        orders.append(
            {
                "order_no": f"HZ-{user_id:03d}-{1000 + order_id}",
                "date": created_at[:10],
                "status": row["status"],
                "total": format_price_cents(int(row["total_cents"])),
                "items": items_by_order.get(order_id, []),
            }
        )

    return orders


def list_all_orders() -> list[dict[str, Any]]:
    """hier wordt een admin-overzicht gebouwd met alle orderdetails en gegroepeerde items per bestelling."""
    order_rows = get_db().execute(
        """
        SELECT
            orders.id,
            orders.user_id,
            orders.status,
            orders.total_cents,
            orders.customer_name,
            orders.customer_email,
            orders.address_line,
            orders.postal_code,
            orders.city,
            orders.phone,
            orders.notes,
            orders.created_at,
            users.name AS account_name,
            users.email AS account_email
        FROM orders
        JOIN users ON users.id = orders.user_id
        ORDER BY orders.id DESC
        """
    ).fetchall()

    if not order_rows:
        return []

    order_ids = [int(row["id"]) for row in order_rows]
    placeholders = ",".join(["?"] * len(order_ids))
    item_rows = get_db().execute(
        f"""
        SELECT order_id, book_id, title, quantity
        FROM order_items
        WHERE order_id IN ({placeholders})
        ORDER BY id
        """,
        order_ids,
    ).fetchall()

    items_by_order: dict[int, list[dict[str, Any]]] = {order_id: [] for order_id in order_ids}
    for row in item_rows:
        title = str(row["title"])
        quantity = int(row["quantity"])
        label = f"{title} x{quantity}" if quantity > 1 else title
        items_by_order[int(row["order_id"])].append(
            {
                "title": label,
                "book_id": int(row["book_id"]),
            }
        )

    orders: list[dict[str, Any]] = []
    for row in order_rows:
        order_id = int(row["id"])
        created_at = str(row["created_at"])
        orders.append(
            {
                "id": order_id,
                "order_no": f"HZ-{int(row['user_id']):03d}-{1000 + order_id}",
                "date": created_at[:10],
                "status": row["status"],
                "total": format_price_cents(int(row["total_cents"])),
                "user_name": row["account_name"],
                "user_email": row["account_email"],
                "customer_name": row["customer_name"],
                "customer_email": row["customer_email"],
                "address_line": row["address_line"],
                "postal_code": row["postal_code"],
                "city": row["city"],
                "phone": row["phone"],
                "notes": row["notes"],
                "items": items_by_order.get(order_id, []),
            }
        )

    return orders


def get_order_by_id(order_id: int) -> sqlite3.Row | None:
    """ophalen van de order header nodig voor admin acties."""
    return get_db().execute(
        "SELECT id, user_id FROM orders WHERE id = ?",
        (order_id,),
    ).fetchone()


def delete_order(order_id: int) -> None:
    """verwijderen van een bestelling en laten cascaderen naar gerelateerde rijen."""
    db = get_db()
    db.execute("DELETE FROM orders WHERE id = ?", (order_id,))
    db.commit()


def update_order_status(order_id: int, status: str) -> None:
    """updaten van statusveld voor één bestelling."""
    db = get_db()
    db.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
    db.commit()
