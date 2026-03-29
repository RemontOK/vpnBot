from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_db
from ..models import Customer, Order, OrderStatus, Plan
from ..schemas import OrderCreateIn, OrderOut, PlanOut, ProfileOut
from ..services.marzban import MarzbanClient

router = APIRouter(prefix='/api', tags=['public'])
marzban = MarzbanClient()


@router.get('/health')
async def health() -> dict:
    return {'ok': True}


@router.get('/plans', response_model=list[PlanOut])
async def plans(db: AsyncSession = Depends(get_db)) -> list[PlanOut]:
    rows = await db.scalars(select(Plan).where(Plan.is_active.is_(True)).order_by(Plan.price_rub.asc()))
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


@router.post('/orders', response_model=OrderOut)
async def create_order(payload: OrderCreateIn, db: AsyncSession = Depends(get_db)) -> OrderOut:
    plan = await db.get(Plan, payload.plan_id)
    if not plan or not plan.is_active:
        raise HTTPException(status_code=404, detail='Plan not found')

    customer = await _get_or_create_customer(db, payload.telegram_id, payload.username, payload.first_name)
    active_profile = await _build_profile(customer)
    if active_profile and active_profile.status == 'active':
        raise HTTPException(
            status_code=409,
            detail={
                'message': 'Subscription already active',
                'profile': active_profile.model_dump(mode='json'),
            },
        )

    order = Order(
        customer_id=customer.id,
        plan_id=plan.id,
        amount_rub=plan.price_rub,
        status=OrderStatus.pending,
        yookassa_payment_id=f'demo-{customer.telegram_id}-{int(datetime.now(timezone.utc).timestamp())}',
        yookassa_confirmation_url='demo://checkout',
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)

    return _to_order_out(order, plan)


@router.post('/orders/{order_id}/demo-pay', response_model=OrderOut)
async def demo_pay_order(order_id: str, db: AsyncSession = Depends(get_db)) -> OrderOut:
    order = await db.scalar(
        select(Order)
        .where(Order.id == order_id)
        .options(selectinload(Order.plan), selectinload(Order.customer))
    )
    if not order:
        raise HTTPException(status_code=404, detail='Order not found')

    if order.status != OrderStatus.paid:
        await _provision_order(order)
        await db.commit()
        await db.refresh(order)

    return _to_order_out(order, order.plan)


@router.get('/orders/{order_id}', response_model=OrderOut)
async def order_status(order_id: str, db: AsyncSession = Depends(get_db)) -> OrderOut:
    order = await db.scalar(
        select(Order)
        .where(Order.id == order_id)
        .options(selectinload(Order.plan), selectinload(Order.customer))
    )
    if not order:
        raise HTTPException(status_code=404, detail='Order not found')

    return _to_order_out(order, order.plan)


@router.get('/profile/{telegram_id}', response_model=ProfileOut)
async def profile(telegram_id: int, db: AsyncSession = Depends(get_db)) -> ProfileOut:
    customer = await db.scalar(
        select(Customer)
        .where(Customer.telegram_id == telegram_id)
        .options(selectinload(Customer.orders).selectinload(Order.plan))
    )
    if not customer:
        return ProfileOut(has_subscription=False, status='new')

    profile_data = await _build_profile(customer)
    return profile_data or ProfileOut(has_subscription=False, status='inactive')


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
    provision = await marzban.create_user(
        telegram_id=order.customer.telegram_id,
        duration_days=order.plan.duration_days,
        data_limit_gb=order.plan.data_limit_gb,
    )
    order.status = OrderStatus.paid
    order.marzban_username = provision['username']
    order.marzban_subscription_url = provision['subscription_url']
    order.paid_at = datetime.now(timezone.utc)


async def _build_profile(customer: Customer) -> ProfileOut | None:
    paid_orders = [order for order in customer.orders if order.status == OrderStatus.paid and order.paid_at]
    if not paid_orders:
        return None

    latest = max(paid_orders, key=lambda item: item.paid_at or item.created_at)
    expires_at = (latest.paid_at or latest.created_at) + timedelta(days=latest.plan.duration_days)
    now = datetime.now(timezone.utc)
    days_left = max(0, (expires_at - now).days)
    status = 'active' if expires_at > now else 'expired'

    if latest.marzban_username:
        user = await marzban.get_user(latest.marzban_username)
        if not user:
            return ProfileOut(has_subscription=False, status='inactive')
        remote_status = user.get('status')
        if remote_status and remote_status != 'active':
            return ProfileOut(has_subscription=False, status='inactive')

    return ProfileOut(
        has_subscription=True,
        status=status,
        plan_title=latest.plan.title,
        duration_days=latest.plan.duration_days,
        data_limit_gb=latest.plan.data_limit_gb,
        amount_rub=latest.amount_rub,
        days_left=days_left,
        expires_at=expires_at,
        subscription_url=latest.marzban_subscription_url,
        marzban_username=latest.marzban_username,
        auto_renew_enabled=False,
    )


def _to_order_out(order: Order, plan: Plan) -> OrderOut:
    return OrderOut(
        id=order.id,
        status=order.status,
        amount_rub=order.amount_rub,
        plan_title=plan.title,
        duration_days=plan.duration_days,
        data_limit_gb=plan.data_limit_gb,
        confirmation_url=order.yookassa_confirmation_url,
        subscription_url=order.marzban_subscription_url,
        marzban_username=order.marzban_username,
        paid_at=order.paid_at,
        created_at=order.created_at,
    )
