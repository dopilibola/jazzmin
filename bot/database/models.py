"""
SQLAlchemy 2.0 async ORM models for grave care service.
Clean schema: User, Service, Flower, CartItem, Order, OrderItem.
"""
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


# -----------------------------------------------------------------------------
# User
# -----------------------------------------------------------------------------


class User(Base):
    """Customer profile (Telegram user)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    phone_number: Mapped[str] = mapped_column(String(30), default="", nullable=False)
    language: Mapped[str] = mapped_column(String(5), default="ru", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    cart_items: Mapped[list["CartItem"]] = relationship(
        "CartItem", back_populates="user", cascade="all, delete-orphan"
    )
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="user")
    support_messages: Mapped[list["SupportMessage"]] = relationship(
        "SupportMessage", back_populates="user"
    )
    graves: Mapped[list["Grave"]] = relationship(
        "Grave", back_populates="user", cascade="all, delete-orphan"
    )


# -----------------------------------------------------------------------------
# Grave (user's saved graves - relatives)
# -----------------------------------------------------------------------------

RELATIONSHIP_DEFAULT = "Blood Relative"
RELATIONSHIP_CHOICES = [
    "Grandmother",
    "Grandfather",
    "Mother",
    "Father",
    "Brother",
    "Sister",
    "Uncle",
    "Aunt",
    "Other",
]


class Grave(Base):
    """User's saved grave (relative)."""

    __tablename__ = "graves"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    region: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    district: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    cemetery: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    deceased_full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    birth_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    birth_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    birth_approximate: Mapped[bool] = mapped_column(default=False, nullable=False)
    death_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    death_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    death_approximate: Mapped[bool] = mapped_column(default=False, nullable=False)
    relationship_status: Mapped[str] = mapped_column(
        String(50), default=RELATIONSHIP_DEFAULT, nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="graves")


# -----------------------------------------------------------------------------
# Service (grave cleaning, monument, etc.)
# -----------------------------------------------------------------------------


class Service(Base):
    """Grave care service (cleaning, marble, monument)."""

    __tablename__ = "services"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name_en: Mapped[str] = mapped_column(String(200), nullable=False)
    name_ru: Mapped[str] = mapped_column(String(200), nullable=False)
    name_uz: Mapped[str] = mapped_column(String(200), nullable=False)
    description_en: Mapped[str] = mapped_column(Text, default="", nullable=False)
    description_ru: Mapped[str] = mapped_column(Text, default="", nullable=False)
    description_uz: Mapped[str] = mapped_column(Text, default="", nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[str] = mapped_column(String(50), default="cleaning", nullable=False)

    def get_name(self, lang: str) -> str:
        return getattr(self, f"name_{lang}", self.name_en)

    def get_description(self, lang: str) -> str:
        return getattr(self, f"description_{lang}", self.description_en)


# -----------------------------------------------------------------------------
# Flower (legacy - kept for backward compat)
# -----------------------------------------------------------------------------


class Flower(Base):
    """Flower product for grave decoration (legacy)."""

    __tablename__ = "flowers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name_en: Mapped[str] = mapped_column(String(200), nullable=False)
    name_ru: Mapped[str] = mapped_column(String(200), nullable=False)
    name_uz: Mapped[str] = mapped_column(String(200), nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    image_file_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    def get_name(self, lang: str) -> str:
        return getattr(self, f"name_{lang}", self.name_en)


# -----------------------------------------------------------------------------
# Flower Categories and Products (flower feature module)
# -----------------------------------------------------------------------------


class FlowerCategory(Base):
    """Flower category: planted around grave or placed on grave."""

    __tablename__ = "flower_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name_en: Mapped[str] = mapped_column(String(200), nullable=False)
    name_ru: Mapped[str] = mapped_column(String(200), nullable=False)
    name_uz: Mapped[str] = mapped_column(String(200), nullable=False)

    products: Mapped[list["FlowerProduct"]] = relationship(
        "FlowerProduct", back_populates="category", lazy="selectin"
    )

    def get_name(self, lang: str) -> str:
        return getattr(self, f"name_{lang}", self.name_en)


class FlowerProduct(Base):
    """Flower product: image, name, description, price."""

    __tablename__ = "flower_products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("flower_categories.id", ondelete="CASCADE"), nullable=False
    )
    name_en: Mapped[str] = mapped_column(String(200), nullable=False)
    name_ru: Mapped[str] = mapped_column(String(200), nullable=False)
    name_uz: Mapped[str] = mapped_column(String(200), nullable=False)
    description_en: Mapped[str] = mapped_column(Text, default="", nullable=False)
    description_ru: Mapped[str] = mapped_column(Text, default="", nullable=False)
    description_uz: Mapped[str] = mapped_column(Text, default="", nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    image_file_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    category: Mapped["FlowerCategory"] = relationship(
        "FlowerCategory", back_populates="products"
    )

    def get_name(self, lang: str) -> str:
        return getattr(self, f"name_{lang}", self.name_en)

    def get_description(self, lang: str) -> str:
        return getattr(self, f"description_{lang}", self.description_en)


# -----------------------------------------------------------------------------
# CartItem (user_id, item_type, item_id, quantity, price)
# -----------------------------------------------------------------------------


class CartItem(Base):
    """Item in user's cart. item_type: 'service' or 'flower'."""

    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    item_type: Mapped[str] = mapped_column(String(20), nullable=False)  # service, flower
    item_id: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="cart_items")


# -----------------------------------------------------------------------------
# Region, District, Cemetery (location for orders)
# -----------------------------------------------------------------------------


class Region(Base):
    """Region (oblast/state)."""

    __tablename__ = "regions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name_en: Mapped[str] = mapped_column(String(100), nullable=False)
    name_ru: Mapped[str] = mapped_column(String(100), nullable=False)
    name_uz: Mapped[str] = mapped_column(String(100), nullable=False)

    districts: Mapped[list["District"]] = relationship(
        "District", back_populates="region", lazy="selectin"
    )

    def get_name(self, lang: str) -> str:
        return getattr(self, f"name_{lang}", self.name_ru)


class District(Base):
    """District within a region."""

    __tablename__ = "districts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    region_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("regions.id", ondelete="CASCADE"), nullable=False
    )
    name_en: Mapped[str] = mapped_column(String(100), nullable=False)
    name_ru: Mapped[str] = mapped_column(String(100), nullable=False)
    name_uz: Mapped[str] = mapped_column(String(100), nullable=False)

    region: Mapped["Region"] = relationship("Region", back_populates="districts")
    cemeteries: Mapped[list["Cemetery"]] = relationship(
        "Cemetery", back_populates="district", lazy="selectin"
    )

    def get_name(self, lang: str) -> str:
        return getattr(self, f"name_{lang}", self.name_ru)


class Cemetery(Base):
    """Cemetery within a district."""

    __tablename__ = "cemeteries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    district_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("districts.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    district: Mapped["District"] = relationship("District", back_populates="cemeteries")


# -----------------------------------------------------------------------------
# Order and OrderItem
# -----------------------------------------------------------------------------

# Order statuses as per requirements
ORDER_STATUS_NEW = "new"
ORDER_STATUS_PENDING_PAYMENT = "pending_payment"
ORDER_STATUS_PAYMENT_REVIEW = "payment_review"
ORDER_STATUS_PAID = "paid"
ORDER_STATUS_IN_PROGRESS = "in_progress"
ORDER_STATUS_COMPLETED = "completed"
ORDER_STATUS_CANCELLED = "cancelled"


class Order(Base):
    """Grave care service order with full checkout data."""

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    full_name: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    phone_number: Mapped[str] = mapped_column(String(30), default="", nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    region_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("regions.id", ondelete="SET NULL"), nullable=True
    )
    district_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("districts.id", ondelete="SET NULL"), nullable=True
    )
    cemetery_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("cemeteries.id", ondelete="SET NULL"), nullable=True
    )
    deceased_full_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    birth_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    death_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_price: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    payment_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    receipt_file_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), default=ORDER_STATUS_NEW, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="orders")
    region: Mapped["Region | None"] = relationship("Region", lazy="selectin")
    district: Mapped["District | None"] = relationship("District", lazy="selectin")
    cemetery: Mapped["Cemetery | None"] = relationship("Cemetery", lazy="selectin")
    items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )


class OrderItem(Base):
    """Line item in an order. item_type: 'service', 'flower', or 'flower_product'."""

    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    item_type: Mapped[str] = mapped_column(String(30), nullable=False)
    item_id: Mapped[int] = mapped_column(Integer, nullable=False)  # product_id for flower_product
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)

    order: Mapped["Order"] = relationship("Order", back_populates="items")


# -----------------------------------------------------------------------------
# Support
# -----------------------------------------------------------------------------


class SupportMessage(Base):
    """User support/contact message. Forwarded to admin."""

    __tablename__ = "support_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="support_messages")
