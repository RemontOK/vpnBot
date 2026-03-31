import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class OrderStatus(str, enum.Enum):
    pending = "pending"
    waiting_for_capture = "waiting_for_capture"
    paid = "paid"
    canceled = "canceled"


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    orders: Mapped[list["Order"]] = relationship(back_populates="customer")


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(100))
    emoji: Mapped[str] = mapped_column(String(20), default="🔒")
    price_rub: Mapped[int] = mapped_column(Integer)
    duration_days: Mapped[int] = mapped_column(Integer)
    data_limit_gb: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(default=True)

    orders: Mapped[list["Order"]] = relationship(back_populates="plan")


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"))
    protocol: Mapped[str] = mapped_column(String(32), default="multi")
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus), default=OrderStatus.pending
    )
    amount_rub: Mapped[int] = mapped_column(Integer)

    yookassa_payment_id: Mapped[str] = mapped_column(String(100), unique=True)
    yookassa_confirmation_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    vless_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    vless_uuid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    vless_subscription_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    hysteria_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    hysteria_subscription_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    customer: Mapped[Customer] = relationship(back_populates="orders")
    plan: Mapped[Plan] = relationship(back_populates="orders")
