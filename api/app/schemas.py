import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from .models import OrderStatus


class PlanOut(BaseModel):
    id: int
    code: str
    title: str
    emoji: str
    price_rub: int
    duration_days: int
    data_limit_gb: int


class OrderCreateIn(BaseModel):
    telegram_id: int
    username: str | None = None
    first_name: str | None = None
    plan_id: int


class OrderOut(BaseModel):
    id: uuid.UUID
    status: OrderStatus
    amount_rub: int
    protocol: str = Field(default="multi")
    plan_title: str | None = Field(default=None)
    duration_days: int | None = Field(default=None)
    data_limit_gb: int | None = Field(default=None)
    confirmation_url: str | None = Field(default=None)
    vless_url: str | None = Field(default=None)
    vless_subscription_url: str | None = Field(default=None)
    vless_username: str | None = Field(default=None)
    hysteria_subscription_url: str | None = Field(default=None)
    hysteria_username: str | None = Field(default=None)
    paid_at: datetime | None = Field(default=None)
    created_at: datetime


class ProfileOut(BaseModel):
    has_subscription: bool
    status: str
    plan_title: str | None = None
    duration_days: int | None = None
    data_limit_gb: int | None = None
    amount_rub: int | None = None
    days_left: int | None = None
    expires_at: datetime | None = None
    vless_url: str | None = None
    vless_subscription_url: str | None = None
    vless_username: str | None = None
    hysteria_subscription_url: str | None = None
    hysteria_username: str | None = None
    auto_renew_enabled: bool = False


class ActiveSubscriptionError(BaseModel):
    detail: str
    profile: ProfileOut


class YooKassaWebhookEvent(BaseModel):
    event: str
    object: dict
