from typing import TypedDict

from sqlalchemy import select, update

from services.books import format_price_cents
from services.db import get_db
from services.models import Order, OrderItem, User


class CartBookRef(TypedDict):
    id: int
    title: str


class CartItem(TypedDict):
    book: CartBookRef
    quantity: int
    unit_price_cents: int
    line_total_cents: int


class OrderLineSummary(TypedDict):
    title: str
    book_id: int


class UserOrderSummary(TypedDict):
    order_no: str
    date: str
    status: str
    total: str
    items: list[OrderLineSummary]


class AdminOrderSummary(TypedDict):
    id: int
    order_no: str
    date: str
    status: str
    total: str
    user_name: str
    user_email: str
    customer_name: str
    customer_email: str
    address_line: str
    postal_code: str
    city: str
    phone: str
    notes: str
    items: list[OrderLineSummary]


class OrderHeader(TypedDict):
    id: int
    user_id: int


def create_order_for_user(
    user_id: int,
    cart_items: list[CartItem],
    total_cents: int,
    checkout_details: dict[str, str],
) -> int:
    """eerst orderknop wegschrijven en daarna losse orderregels toevoegen."""
    db = get_db()
    order = Order(
        user_id=user_id,
        status="In behandeling",
        total_cents=total_cents,
        customer_name=checkout_details.get("customer_name", ""),
        customer_email=checkout_details.get("customer_email", ""),
        address_line=checkout_details.get("address_line", ""),
        postal_code=checkout_details.get("postal_code", ""),
        city=checkout_details.get("city", ""),
        phone=checkout_details.get("phone", ""),
        notes=checkout_details.get("notes", ""),
    )
    db.add(order)
    db.flush()

    for item in cart_items:
        db.add(
            OrderItem(
                order_id=int(order.id),
                book_id=int(item["book"]["id"]),
                title=str(item["book"]["title"]),
                unit_price_cents=int(item["unit_price_cents"]),
                quantity=int(item["quantity"]),
                line_total_cents=int(item["line_total_cents"]),
            )
        )

    db.commit()
    return int(order.id)


def list_user_orders(user_id: int, limit: int | None = None) -> list[UserOrderSummary]:
    """combineren van order- en itemregels tot compacte cards voor de accountweergave."""
    db = get_db()
    statement = select(Order).where(Order.user_id == user_id).order_by(Order.id.desc())
    if limit is not None:
        statement = statement.limit(limit)

    order_rows = db.scalars(statement).all()
    if not order_rows:
        return []

    order_ids = [int(order.id) for order in order_rows]
    item_rows = db.scalars(select(OrderItem).where(OrderItem.order_id.in_(order_ids)).order_by(OrderItem.id)).all()

    items_by_order: dict[int, list[OrderLineSummary]] = {order_id: [] for order_id in order_ids}
    for row in item_rows:
        title = str(row.title)
        quantity = int(row.quantity)
        label = f"{title} x{quantity}" if quantity > 1 else title
        items_by_order[int(row.order_id)].append({"title": label, "book_id": int(row.book_id)})

    orders: list[UserOrderSummary] = []
    for row in order_rows:
        created_at = str(row.created_at)
        order_id = int(row.id)
        orders.append(
            {
                "order_no": f"HZ-{user_id:03d}-{1000 + order_id}",
                "date": created_at[:10],
                "status": row.status,
                "total": format_price_cents(int(row.total_cents)),
                "items": items_by_order.get(order_id, []),
            }
        )

    return orders


def list_all_orders() -> list[AdminOrderSummary]:
    """hier wordt een admin-overzicht gebouwd met alle orderdetails en gegroepeerde items per bestelling."""
    db = get_db()
    order_rows = db.execute(select(Order, User).join(User, User.id == Order.user_id).order_by(Order.id.desc())).all()

    if not order_rows:
        return []

    orders_only = [row[0] for row in order_rows]
    order_ids = [int(order.id) for order in orders_only]
    item_rows = db.scalars(select(OrderItem).where(OrderItem.order_id.in_(order_ids)).order_by(OrderItem.id)).all()

    items_by_order: dict[int, list[OrderLineSummary]] = {order_id: [] for order_id in order_ids}
    for row in item_rows:
        title = str(row.title)
        quantity = int(row.quantity)
        label = f"{title} x{quantity}" if quantity > 1 else title
        items_by_order[int(row.order_id)].append({"title": label, "book_id": int(row.book_id)})

    orders: list[AdminOrderSummary] = []
    for order, account in order_rows:
        order_id = int(order.id)
        created_at = str(order.created_at)
        orders.append(
            {
                "id": order_id,
                "order_no": f"HZ-{int(order.user_id):03d}-{1000 + order_id}",
                "date": created_at[:10],
                "status": order.status,
                "total": format_price_cents(int(order.total_cents)),
                "user_name": account.name,
                "user_email": account.email,
                "customer_name": order.customer_name,
                "customer_email": order.customer_email,
                "address_line": order.address_line,
                "postal_code": order.postal_code,
                "city": order.city,
                "phone": order.phone,
                "notes": order.notes,
                "items": items_by_order.get(order_id, []),
            }
        )

    return orders


def get_order_by_id(order_id: int) -> OrderHeader | None:
    """ophalen van de order header nodig voor admin acties."""
    order = get_db().get(Order, order_id)
    if order is None:
        return None
    return {"id": order.id, "user_id": order.user_id}


def delete_order(order_id: int) -> None:
    """verwijderen van een bestelling en laten cascaderen naar gerelateerde rijen."""
    db = get_db()
    order = db.get(Order, order_id)
    if order is not None:
        db.delete(order)
    db.commit()


def update_order_status(order_id: int, status: str) -> None:
    """updaten van statusveld voor één bestelling."""
    db = get_db()
    db.execute(update(Order).where(Order.id == order_id).values(status=status))
    db.commit()