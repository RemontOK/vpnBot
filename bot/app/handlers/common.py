from datetime import datetime

import httpx
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from ..keyboards import (
    apps_keyboard,
    checkout_keyboard,
    main_menu,
    plans_keyboard,
    profile_actions_keyboard,
)
from ..services.api_client import BackendClient
from ..texts import APPS_TEXT, HELP_TEXT, SUPPORT_TEXT, WELCOME_TEXT

router = Router()
api = BackendClient()


@router.message(Command("start"))
async def start(message: Message) -> None:
    await message.answer(WELCOME_TEXT, parse_mode="HTML", reply_markup=main_menu())


@router.message(Command("plans"))
@router.message(F.text == "💳 Купить подписку")
async def show_plans(message: Message) -> None:
    profile_data = await api.get_profile(message.from_user.id)
    if profile_data["has_subscription"] and profile_data["status"] == "active":
        await message.answer(
            "У вас уже есть активная подписка. Ниже текущий профиль.",
            reply_markup=main_menu(),
        )
        await message.answer(
            _format_profile(profile_data),
            parse_mode="HTML",
            reply_markup=profile_actions_keyboard(),
            disable_web_page_preview=True,
        )
        return

    plans = await api.get_plans()
    await message.answer(
        "<b>Тарифы</b>\nПосле оплаты будет доступна ссылка VLESS.",
        parse_mode="HTML",
        reply_markup=plans_keyboard(plans),
    )


@router.message(F.text == "👤 Мой профиль")
async def profile(message: Message) -> None:
    await message.answer(
        _format_profile(await api.get_profile(message.from_user.id)),
        parse_mode="HTML",
        reply_markup=profile_actions_keyboard(),
        disable_web_page_preview=True,
    )


@router.message(F.text == "📱 Приложения")
async def apps(message: Message) -> None:
    await message.answer(
        APPS_TEXT,
        parse_mode="HTML",
        reply_markup=apps_keyboard(),
        disable_web_page_preview=True,
    )


@router.message(Command("support"))
@router.message(F.text == "❓ Помощь")
async def support(message: Message) -> None:
    await message.answer(HELP_TEXT + "\n\n" + SUPPORT_TEXT, parse_mode="HTML")


@router.callback_query(F.data == "menu:main")
async def menu_main(callback: CallbackQuery) -> None:
    await callback.message.answer(
        WELCOME_TEXT, parse_mode="HTML", reply_markup=main_menu()
    )
    await callback.answer()


@router.callback_query(F.data == "menu:plans")
async def menu_plans(callback: CallbackQuery) -> None:
    profile_data = await api.get_profile(callback.from_user.id)
    if profile_data["has_subscription"] and profile_data["status"] == "active":
        await callback.message.answer(
            "У вас уже есть активная подписка. Ниже текущий профиль.",
            reply_markup=main_menu(),
        )
        await callback.message.answer(
            _format_profile(profile_data),
            parse_mode="HTML",
            reply_markup=profile_actions_keyboard(),
            disable_web_page_preview=True,
        )
        await callback.answer()
        return

    plans = await api.get_plans()
    await callback.message.answer(
        "<b>Тарифы</b>\nПосле оплаты будет доступна ссылка VLESS.",
        parse_mode="HTML",
        reply_markup=plans_keyboard(plans),
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^buy:\d+$"))
async def buy_plan(callback: CallbackQuery) -> None:
    plan_id = int(callback.data.split(":")[1])
    try:
        order = await api.create_order(
            telegram_id=callback.from_user.id,
            username=callback.from_user.username,
            first_name=callback.from_user.first_name,
            plan_id=plan_id,
        )
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 409:
            payload = exc.response.json()
            profile_data = payload["detail"]["profile"]
            await callback.message.answer(
                "У вас уже есть активная подписка. Показываю текущий профиль.",
                reply_markup=main_menu(),
            )
            await callback.message.answer(
                _format_profile(profile_data),
                parse_mode="HTML",
                reply_markup=profile_actions_keyboard(),
                disable_web_page_preview=True,
            )
            await callback.answer()
            return
        raise

    await callback.message.answer(
        (
            "<b>Новый заказ</b>\n\n"
            f"Тариф: <b>{order['plan_title']}</b>\n"
            "Доступ после оплаты: <b>VLESS</b>\n"
            f"Срок: {order['duration_days']} дн.\n"
            f"К оплате: <b>{order['amount_rub']} RUB</b>\n\n"
            "После оплаты в профиле будет доступна ссылка."
        ),
        parse_mode="HTML",
        reply_markup=checkout_keyboard(str(order["id"]), order.get("confirmation_url")),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("check:"))
async def check_payment(callback: CallbackQuery) -> None:
    order_id = callback.data.split(":", 1)[1]
    order = await api.get_order(order_id)

    if order["status"] == "paid" and order.get("vless_subscription_url"):
        await callback.message.answer(
            _format_order_success(order),
            parse_mode="HTML",
            reply_markup=profile_actions_keyboard(),
            disable_web_page_preview=True,
        )
    elif order["status"] == "canceled":
        await callback.message.answer(
            "Платеж отменён. Создайте новый заказ и попробуйте снова."
        )
    else:
        await callback.message.answer(
            "Платёж ещё не подтверждён. Если вы уже оплатили, нажмите кнопку позже ещё раз."
        )

    await callback.answer()


@router.callback_query(F.data == "profile:refresh")
async def refresh_profile(callback: CallbackQuery) -> None:
    profile_data = await api.refresh_profile(callback.from_user.id)
    await callback.message.answer(
        _format_profile(profile_data),
        parse_mode="HTML",
        reply_markup=profile_actions_keyboard(),
        disable_web_page_preview=True,
    )
    await callback.answer("Ссылка обновлена.")


def _format_profile(profile_data: dict) -> str:
    if not profile_data["has_subscription"]:
        return (
            "<b>У вас нет подписки</b>\n\n"
            "Активная подписка пока не найдена.\n"
            "Нажмите <b>Купить подписку</b>, чтобы оформить доступ."
        )

    expires_at = _format_dt(profile_data.get("expires_at"))
    parts = [
        "<b>Ваш профиль</b>\n",
        f"Тариф: {profile_data['plan_title']}",
        f"Дней осталось: {profile_data['days_left']}",
        f"Действует до: {expires_at}",
    ]

    if profile_data.get("status") != "active":
        parts.extend(
            [
                "",
                "Статус: доступ требует обновления.",
                "Нажмите <b>Обновить ссылку</b>, чтобы перевыпустить подключение.",
            ]
        )
        return "\n".join(parts).strip()

    parts.extend(["", "<b>Ссылка для подключения</b>"])
    if profile_data.get("vless_subscription_url"):
        parts.extend(
            [
                "VLESS:",
                f"<code>{profile_data['vless_subscription_url']}</code>",
                "",
            ]
        )

    return "\n".join(parts).strip()


def _format_order_success(order: dict) -> str:
    paid_at = _format_dt(order.get("paid_at"))
    parts = [
        "<b>Подписка активирована</b>\n",
        f"Тариф: {order['plan_title']}",
        f"Оплачено: {paid_at}",
        "",
        "<b>Ссылка для подключения</b>",
    ]

    if order.get("vless_subscription_url"):
        parts.extend(
            [
                "VLESS:",
                f"<code>{order['vless_subscription_url']}</code>",
                "",
            ]
        )

    parts.append("Используйте Nekoray, v2rayNG или Hiddify.")
    return "\n".join(parts).strip()


def _format_dt(value: str | None) -> str:
    if not value:
        return "-"
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt.strftime("%d.%m.%Y %H:%M")
