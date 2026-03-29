from datetime import datetime

import httpx
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from ..keyboards import (
    apps_keyboard,
    demo_checkout_keyboard,
    demo_payment_confirm_keyboard,
    main_menu,
    plans_keyboard,
    profile_actions_keyboard,
)
from ..services.api_client import BackendClient
from ..texts import APPS_TEXT, HELP_TEXT, SUPPORT_TEXT, WELCOME_TEXT

router = Router()
api = BackendClient()


@router.message(Command('start'))
async def start(message: Message) -> None:
    await message.answer(WELCOME_TEXT, parse_mode='HTML', reply_markup=main_menu())


@router.message(Command('plans'))
@router.message(F.text == '\U0001F4B3 Купить подписку')
async def show_plans(message: Message) -> None:
    profile_data = await api.get_profile(message.from_user.id)
    if profile_data['has_subscription'] and profile_data['status'] == 'active':
        await message.answer(
            'Подписка уже активна. Ниже текущая конфигурация.',
            reply_markup=main_menu(),
        )
        await message.answer(
            _format_profile(profile_data),
            parse_mode='HTML',
            reply_markup=profile_actions_keyboard(),
            disable_web_page_preview=True,
        )
        return

    plans = await api.get_plans()
    await message.answer(
        '<b>Подписка</b>\nВыбери вариант покупки:',
        parse_mode='HTML',
        reply_markup=plans_keyboard(plans),
    )


@router.message(F.text == '\U0001F464 Мой профиль')
async def profile(message: Message) -> None:
    await message.answer(
        _format_profile(await api.get_profile(message.from_user.id)),
        parse_mode='HTML',
        reply_markup=profile_actions_keyboard(),
        disable_web_page_preview=True,
    )


@router.message(F.text == '\U0001F4F1 Приложения')
async def apps(message: Message) -> None:
    await message.answer(APPS_TEXT, parse_mode='HTML', reply_markup=apps_keyboard(), disable_web_page_preview=True)


@router.message(Command('support'))
@router.message(F.text == '\u2753 Помощь')
async def support(message: Message) -> None:
    await message.answer(HELP_TEXT + '\n\n' + SUPPORT_TEXT, parse_mode='HTML')


@router.callback_query(F.data == 'menu:main')
async def menu_main(callback: CallbackQuery) -> None:
    await callback.message.answer(WELCOME_TEXT, parse_mode='HTML', reply_markup=main_menu())
    await callback.answer()


@router.callback_query(F.data == 'menu:plans')
async def menu_plans(callback: CallbackQuery) -> None:
    profile_data = await api.get_profile(callback.from_user.id)
    if profile_data['has_subscription'] and profile_data['status'] == 'active':
        await callback.message.answer(
            'Подписка уже активна. Ниже текущая конфигурация.',
            reply_markup=main_menu(),
        )
        await callback.message.answer(
            _format_profile(profile_data),
            parse_mode='HTML',
            reply_markup=profile_actions_keyboard(),
            disable_web_page_preview=True,
        )
        await callback.answer()
        return

    plans = await api.get_plans()
    await callback.message.answer(
        '<b>Подписка</b>\nВыбери вариант покупки:',
        parse_mode='HTML',
        reply_markup=plans_keyboard(plans),
    )
    await callback.answer()


@router.callback_query(F.data.startswith('buy:'))
async def buy_plan(callback: CallbackQuery) -> None:
    plan_id = int(callback.data.split(':')[1])
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
            profile_data = payload['detail']['profile']
            await callback.message.answer(
                'Подписка уже активна. Повторная покупка сейчас не нужна.',
                reply_markup=main_menu(),
            )
            await callback.message.answer(
                _format_profile(profile_data),
                parse_mode='HTML',
                reply_markup=profile_actions_keyboard(),
                disable_web_page_preview=True,
            )
            await callback.answer()
            return
        raise

    await callback.message.answer(
        (
            '<b>Окно оплаты</b>\n\n'
            f"Подписка: <b>{order['plan_title']}</b>\n"
            f"Срок: {order['duration_days']} дн.\n"
            f"К оплате: <b>{order['amount_rub']} RUB</b>\n\n"
            'Нажми оплатить картой. В demo-режиме после этого можно сразу подтвердить оплату.'
        ),
        parse_mode='HTML',
        reply_markup=demo_checkout_keyboard(str(order['id'])),
    )
    await callback.answer()


@router.callback_query(F.data.startswith('demo:show:'))
async def show_demo_payment(callback: CallbackQuery) -> None:
    order_id = callback.data.split(':', 2)[2]
    await callback.message.answer(
        (
            '<b>Demo payment gateway</b>\n\n'
            'Банк: Demo Bank\n'
            'Карта: 2200 00** **** 4242\n'
            'Статус: ожидает подтверждения\n\n'
            'Нажми <b>Я оплатил</b>, чтобы имитировать успешный платеж.'
        ),
        parse_mode='HTML',
        reply_markup=demo_payment_confirm_keyboard(order_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith('demo:pay:'))
async def demo_pay(callback: CallbackQuery) -> None:
    order_id = callback.data.split(':', 2)[2]
    order = await api.demo_pay(order_id)
    await callback.message.answer(
        _format_order_success(order),
        parse_mode='HTML',
        reply_markup=profile_actions_keyboard(),
        disable_web_page_preview=True,
    )
    await callback.answer('Подписка активирована')


@router.callback_query(F.data.startswith('check:'))
async def check_payment(callback: CallbackQuery) -> None:
    order_id = callback.data.split(':', 1)[1]
    order = await api.get_order(order_id)

    if order['status'] == 'paid' and order.get('subscription_url'):
        await callback.message.answer(
            _format_order_success(order),
            parse_mode='HTML',
            reply_markup=profile_actions_keyboard(),
            disable_web_page_preview=True,
        )
    else:
        await callback.message.answer('Платеж еще не подтвержден. Нажми кнопку оплаты и заверши demo-оплату.')

    await callback.answer()


def _format_profile(profile_data: dict) -> str:
    if not profile_data['has_subscription']:
        return (
            '<b>Ваш профиль</b>\n\n'
            'Подписка еще не оформлена.\n'
            'Нажми <b>Купить подписку</b>, чтобы получить конфигурацию.'
        )

    expires_at = _format_dt(profile_data.get('expires_at'))

    return (
        '<b>Ваш профиль</b>\n\n'
        f"Подписка: {profile_data['plan_title']}\n"
        f"Осталось дней: {profile_data['days_left']}\n\n"
        'Ваша конфигурация:\n'
        f"<code>{profile_data['subscription_url']}</code>\n\n"
        f"Дата окончания: {expires_at}"
    )


def _format_order_success(order: dict) -> str:
    paid_at = _format_dt(order.get('paid_at'))
    return (
        '<b>Оплата подтверждена</b>\n\n'
        f"Логин: <code>{order['marzban_username']}</code>\n"
        f"Подписка: {order['plan_title']}\n"
        f"Активировано: {paid_at}\n\n"
        'Ваша конфигурация:\n'
        f"<code>{order['subscription_url']}</code>\n\n"
        'Добавь ссылку в Nekoray / v2rayNG / Hiddify.'
    )


def _format_dt(value: str | None) -> str:
    if not value:
        return '-'
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    return dt.strftime('%d.%m.%Y %H:%M')
