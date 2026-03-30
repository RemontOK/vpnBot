from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_db
from ..models import Order, OrderStatus
from ..schemas import YooKassaWebhookEvent
from ..services.marzban import MarzbanClient

router = APIRouter(prefix='/api/webhooks', tags=['webhooks'])
marzban = MarzbanClient()


@router.post('/yookassa')
async def yookassa_webhook(payload: YooKassaWebhookEvent, db: AsyncSession = Depends(get_db)) -> dict:
    payment_object = payload.object
    payment_id = payment_object.get('id')
    if not payment_id:
        raise HTTPException(status_code=400, detail='payment id missing')

    order = await db.scalar(
        select(Order)
        .where(Order.yookassa_payment_id == payment_id)
        .options(selectinload(Order.plan), selectinload(Order.customer))
    )
    if not order:
        return {'ok': True, 'skipped': 'order not found'}

    status = (payment_object.get('status') or 'pending').lower()
    order.status = _map_payment_status(status)

    if order.status == OrderStatus.paid:
        if not order.vless_subscription_url:
            vless = await marzban.create_user(
                telegram_id=order.customer.telegram_id,
                duration_days=order.plan.duration_days,
                data_limit_gb=order.plan.data_limit_gb,
                protocol='vless',
            )
            order.vless_username = vless['username']
            order.vless_subscription_url = vless['subscription_url']

        if not order.hysteria_subscription_url:
            hysteria = await marzban.create_user(
                telegram_id=order.customer.telegram_id,
                duration_days=order.plan.duration_days,
                data_limit_gb=order.plan.data_limit_gb,
                protocol='hysteria',
            )
            order.hysteria_username = hysteria['username']
            order.hysteria_subscription_url = hysteria['subscription_url']

        if not order.paid_at:
            order.paid_at = datetime.now(timezone.utc)

    await db.commit()
    return {'ok': True}


def _map_payment_status(status: str) -> OrderStatus:
    if status == 'succeeded':
        return OrderStatus.paid
    if status == 'waiting_for_capture':
        return OrderStatus.waiting_for_capture
    if status == 'canceled':
        return OrderStatus.canceled
    return OrderStatus.pending
