from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import select, text

from .config import settings
from .database import SessionLocal, engine
from .models import Base, Plan
from .routes.public import router as public_router
from .routes.webhooks import router as webhook_router


async def seed_plans() -> None:
    async with SessionLocal() as db:
        desired = {
            'starter': {
                'title': '1 месяц',
                'emoji': '📅',
                'price_rub': settings.plan_starter_price,
                'duration_days': settings.plan_starter_days,
                'data_limit_gb': settings.plan_starter_gb,
            }
        }

        rows = await db.scalars(select(Plan))
        existing = {plan.code: plan for plan in rows}

        for code, plan in existing.items():
            if code not in desired:
                plan.is_active = False

        for code, data in desired.items():
            if code in existing:
                plan = existing[code]
                plan.title = data['title']
                plan.emoji = data['emoji']
                plan.price_rub = data['price_rub']
                plan.duration_days = data['duration_days']
                plan.data_limit_gb = data['data_limit_gb']
                plan.is_active = True
            else:
                db.add(
                    Plan(
                        code=code,
                        title=data['title'],
                        emoji=data['emoji'],
                        price_rub=data['price_rub'],
                        duration_days=data['duration_days'],
                        data_limit_gb=data['data_limit_gb'],
                        is_active=True,
                    )
                )

        await db.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS protocol VARCHAR(32) DEFAULT 'multi'"))
        await conn.execute(text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS vless_username VARCHAR(255)"))
        await conn.execute(text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS vless_subscription_url TEXT"))
        await conn.execute(text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS hysteria_username VARCHAR(255)"))
        await conn.execute(text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS hysteria_subscription_url TEXT"))
    await seed_plans()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(public_router)
app.include_router(webhook_router)
