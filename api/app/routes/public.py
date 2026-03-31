from base64 import b64encode
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..config import settings
from ..database import get_db
from ..models import Customer, Order, OrderStatus, Plan
from ..schemas import OrderCreateIn, OrderOut, PlanOut, ProfileOut
from ..services.marzban import MarzbanClient
from ..services.yookassa import YooKassaClient

router = APIRouter(prefix="/api", tags=["public"])
compat_router = APIRouter(tags=["compat"])
marzban = MarzbanClient()
yookassa = YooKassaClient()


@router.get("/health")
async def health() -> dict:
    return {"ok": True}


@router.get("/plans", response_model=list[PlanOut])
async def plans(db: AsyncSession = Depends(get_db)) -> list[PlanOut]:
    rows = await db.scalars(
        select(Plan).where(Plan.is_active.is_(True)).order_by(Plan.price_rub.asc())
    )
    return [
        PlanOut(
            id=p.id,
            code=p.code,
            title=p.title,
            emoji=p.emoji,
            price_rub=p.price_rub,
            duration_days=p.duration_days,
            data_limit_gb=p.data_limit_gb,
        )
        for p in rows
    ]


@router.post("/orders", response_model=OrderOut)
async def create_order(
    payload: OrderCreateIn, db: AsyncSession = Depends(get_db)
) -> OrderOut:
    plan = await db.get(Plan, payload.plan_id)
    if not plan or not plan.is_active:
        raise HTTPException(status_code=404, detail="Plan not found")

    customer = await _get_or_create_customer(
        db, payload.telegram_id, payload.username, payload.first_name
    )
    active_profile = await _build_profile(customer)
    if active_profile and active_profile.status == "active":
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Subscription already active",
                "profile": active_profile.model_dump(mode="json"),
            },
        )

    order = Order(
        customer_id=customer.id,
        plan_id=plan.id,
        protocol="multi",
        amount_rub=plan.price_rub,
        status=OrderStatus.pending,
        yookassa_payment_id=f"draft-{customer.telegram_id}-{int(datetime.now(timezone.utc).timestamp())}",
        yookassa_confirmation_url=None,
    )
    db.add(order)
    await db.flush()

    payment = await yookassa.create_payment(
        order_id=order.id,
        amount_rub=plan.price_rub,
        description=f"{plan.title} / VLESS+HYSTERIA / tg:{customer.telegram_id}",
    )

    order.yookassa_payment_id = payment["id"]
    order.yookassa_confirmation_url = payment.get("confirmation", {}).get(
        "confirmation_url"
    )
    order.status = _map_payment_status(payment.get("status", "pending"))

    await db.commit()
    await db.refresh(order)

    return _to_order_out(order, plan)


@router.get("/orders/{order_id}", response_model=OrderOut)
async def order_status(order_id: str, db: AsyncSession = Depends(get_db)) -> OrderOut:
    order = await db.scalar(
        select(Order)
        .where(Order.id == order_id)
        .options(selectinload(Order.plan), selectinload(Order.customer))
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status in {OrderStatus.pending, OrderStatus.waiting_for_capture}:
        await _sync_order_payment(order)
        await db.commit()
        await db.refresh(order)

    return _to_order_out(order, order.plan)


@router.get("/profile/{telegram_id}", response_model=ProfileOut)
async def profile(telegram_id: int, db: AsyncSession = Depends(get_db)) -> ProfileOut:
    customer = await db.scalar(
        select(Customer)
        .where(Customer.telegram_id == telegram_id)
        .options(selectinload(Customer.orders).selectinload(Order.plan))
    )
    if not customer:
        return ProfileOut(has_subscription=False, status="new")

    profile_data = await _build_profile(customer)
    return profile_data or ProfileOut(has_subscription=False, status="inactive")


@router.post("/profile/{telegram_id}/refresh", response_model=ProfileOut)
async def refresh_profile(
    telegram_id: int, db: AsyncSession = Depends(get_db)
) -> ProfileOut:
    customer = await db.scalar(
        select(Customer)
        .where(Customer.telegram_id == telegram_id)
        .options(selectinload(Customer.orders).selectinload(Order.plan))
    )
    if not customer:
        return ProfileOut(has_subscription=False, status="new")

    paid_orders = [
        order
        for order in customer.orders
        if order.status == OrderStatus.paid and order.paid_at
    ]
    if not paid_orders:
        return ProfileOut(has_subscription=False, status="inactive")

    latest = max(paid_orders, key=lambda item: item.paid_at or item.created_at)

    recreate_vless = True
    if latest.vless_username:
        user = await marzban.get_user(latest.vless_username)
        recreate_vless = not user or (
            user.get("status") and user.get("status") != "active"
        )
        if user:
            latest.vless_username = user.get("username") or latest.vless_username
            latest.vless_subscription_url = (
                user.get("subscription_url") or latest.vless_subscription_url
            )
            latest.vless_uuid = user.get("uuid") or latest.vless_uuid
            await db.commit()
            await db.refresh(latest)

    if recreate_vless:
        vless = await marzban.create_user(
            telegram_id=latest.customer.telegram_id,
            duration_days=latest.plan.duration_days,
            data_limit_gb=latest.plan.data_limit_gb,
            protocol="vless",
        )
        latest.vless_username = vless["username"]
        latest.vless_subscription_url = vless["subscription_url"]
        latest.vless_uuid = vless.get("uuid")
        await db.commit()
        await db.refresh(latest)

    refreshed_customer = await db.scalar(
        select(Customer)
        .where(Customer.telegram_id == telegram_id)
        .options(selectinload(Customer.orders).selectinload(Order.plan))
    )
    profile_data = await _build_profile(refreshed_customer)
    return profile_data or ProfileOut(has_subscription=False, status="inactive")


async def _get_or_create_customer(
    db: AsyncSession,
    telegram_id: int,
    username: str | None,
    first_name: str | None,
) -> Customer:
    customer = await db.scalar(
        select(Customer)
        .where(Customer.telegram_id == telegram_id)
        .options(selectinload(Customer.orders).selectinload(Order.plan))
    )
    if customer:
        customer.username = username or customer.username
        customer.first_name = first_name or customer.first_name
        await db.flush()
        return customer

    customer = Customer(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        orders=[],
    )
    db.add(customer)
    await db.flush()
    return customer


async def _provision_order(order: Order) -> None:
    if not order.vless_subscription_url:
        vless = await marzban.create_user(
            telegram_id=order.customer.telegram_id,
            duration_days=order.plan.duration_days,
            data_limit_gb=order.plan.data_limit_gb,
            protocol="vless",
        )
        order.vless_username = vless["username"]
        order.vless_subscription_url = vless["subscription_url"]
        order.vless_uuid = vless.get("uuid")

    order.status = OrderStatus.paid
    if not order.paid_at:
        order.paid_at = datetime.now(timezone.utc)


async def _sync_order_payment(order: Order) -> None:
    payment = await yookassa.get_payment(order.yookassa_payment_id)
    order.status = _map_payment_status(payment.get("status", "pending"))
    if order.status == OrderStatus.paid:
        await _provision_order(order)


async def _build_profile(customer: Customer) -> ProfileOut | None:
    paid_orders = [
        order
        for order in customer.orders
        if order.status == OrderStatus.paid and order.paid_at
    ]
    if not paid_orders:
        return None

    latest = max(paid_orders, key=lambda item: item.paid_at or item.created_at)
    expires_at = (latest.paid_at or latest.created_at) + timedelta(
        days=latest.plan.duration_days
    )
    now = datetime.now(timezone.utc)
    days_left = max(0, (expires_at - now).days)
    status = "active" if expires_at > now else "expired"

    if latest.vless_username:
        user = await marzban.get_user(latest.vless_username)
        if not user or (user.get("status") and user.get("status") != "active"):
            status = "inactive"
        else:
            latest.vless_uuid = user.get("uuid") or latest.vless_uuid
            latest.vless_subscription_url = (
                user.get("subscription_url") or latest.vless_subscription_url
            )

    return ProfileOut(
        has_subscription=True,
        status=status,
        plan_title=latest.plan.title,
        duration_days=latest.plan.duration_days,
        data_limit_gb=latest.plan.data_limit_gb,
        amount_rub=latest.amount_rub,
        days_left=days_left,
        expires_at=expires_at,
        vless_url=_display_vless_url(latest.vless_uuid, latest.vless_username),
        vless_subscription_url=_display_subscription_url(
            latest.vless_uuid, latest.vless_subscription_url
        ),
        vless_username=latest.vless_username,
        hysteria_subscription_url=None,
        hysteria_username=None,
        auto_renew_enabled=False,
    )


def _to_order_out(order: Order, plan: Plan) -> OrderOut:
    return OrderOut(
        id=order.id,
        status=order.status,
        amount_rub=order.amount_rub,
        protocol="multi",
        plan_title=plan.title,
        duration_days=plan.duration_days,
        data_limit_gb=plan.data_limit_gb,
        confirmation_url=order.yookassa_confirmation_url,
        vless_url=_display_vless_url(order.vless_uuid, order.vless_username),
        vless_subscription_url=_display_subscription_url(
            order.vless_uuid, order.vless_subscription_url
        ),
        vless_username=order.vless_username,
        hysteria_subscription_url=None,
        hysteria_username=None,
        paid_at=order.paid_at,
        created_at=order.created_at,
    )


def _map_payment_status(status: str) -> OrderStatus:
    normalized = (status or "").strip().lower()
    if normalized == "succeeded":
        return OrderStatus.paid
    if normalized == "waiting_for_capture":
        return OrderStatus.waiting_for_capture
    if normalized == "canceled":
        return OrderStatus.canceled
    return OrderStatus.pending


def _display_vless_url(vless_uuid: str | None, username: str | None) -> str | None:
    return marzban.build_compat_vless_url(vless_uuid, username)


def _display_subscription_url(
    vless_uuid: str | None, raw_subscription_url: str | None
) -> str | None:
    return marzban.build_compat_subscription_url(vless_uuid) or raw_subscription_url


@compat_router.get("/pac{hash}/sub")
async def compat_subscription(
    hash: str,
    id: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
) -> Response:
    if hash != settings.compat_hash:
        raise HTTPException(status_code=404, detail="Subscription not found")

    order = await db.scalar(
        select(Order)
        .where(Order.vless_uuid == id)
        .options(selectinload(Order.customer), selectinload(Order.plan))
        .order_by(Order.paid_at.desc(), Order.created_at.desc())
    )
    if not order or not order.vless_username:
        raise HTTPException(status_code=404, detail="Subscription not found")

    user = await marzban.get_user(order.vless_username)
    compat_vless_url = marzban.build_compat_vless_url(
        order.vless_uuid, order.vless_username
    )
    if not user or not compat_vless_url:
        raise HTTPException(status_code=404, detail="Subscription not found")

    subscription_body = b64encode(f"{compat_vless_url}\n".encode("utf-8")).decode(
        "ascii"
    )
    return Response(
        content=subscription_body,
        media_type="text/plain",
    )
