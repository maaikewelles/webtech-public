from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class BooksBase(DeclarativeBase):
    pass


class UsersBase(DeclarativeBase):
    pass


class Book(BooksBase):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    author: Mapped[str] = mapped_column(String, nullable=False)
    isbn: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    binding: Mapped[str] = mapped_column(String, nullable=False)
    language: Mapped[str] = mapped_column(String, nullable=False)
    genre: Mapped[str] = mapped_column(String, nullable=False, default="Algemeen")
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[str] = mapped_column(String, nullable=False)
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    delivery: Mapped[str] = mapped_column(String, nullable=False)
    stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class SeedState(BooksBase):
    __tablename__ = "seed_state"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(String, nullable=False)


class User(UsersBase):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    is_admin: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    profile_image: Mapped[str] = mapped_column(String, nullable=True)
    last_login: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    orders = relationship("Order", back_populates="user", cascade="all, delete-orphan")
    wishlist_items = relationship("WishlistItem", back_populates="user", cascade="all, delete-orphan")


class WishlistItem(UsersBase):
    __tablename__ = "wishlist"
    __table_args__ = (UniqueConstraint("user_id", "book_id", name="uq_wishlist_user_book"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    book_id: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[str] = mapped_column(String, nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    user = relationship("User", back_populates="wishlist_items")


class Order(UsersBase):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="In behandeling")
    total_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    customer_name: Mapped[str] = mapped_column(String, nullable=False, default="")
    customer_email: Mapped[str] = mapped_column(String, nullable=False, default="")
    address_line: Mapped[str] = mapped_column(String, nullable=False, default="")
    postal_code: Mapped[str] = mapped_column(String, nullable=False, default="")
    city: Mapped[str] = mapped_column(String, nullable=False, default="")
    phone: Mapped[str] = mapped_column(String, nullable=False, default="")
    notes: Mapped[str] = mapped_column(String, nullable=False, default="")
    created_at: Mapped[str] = mapped_column(String, nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(UsersBase):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    book_id: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    unit_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    line_total_cents: Mapped[int] = mapped_column(Integer, nullable=False)

    order = relationship("Order", back_populates="items")