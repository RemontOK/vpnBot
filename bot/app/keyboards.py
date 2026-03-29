from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


V2RAYN_RELEASES_URL = 'https://github.com/2dust/v2rayN/releases/latest'
NEKOBOX_RELEASES_URL = 'https://github.com/MatsuriDayo/NekoBoxForAndroid/releases/latest'
HIDDIFY_DOWNLOAD_URL = 'https://hiddify.com/app/'
HIDDIFY_ANDROID_URL = 'https://play.google.com/store/apps/details?id=app.hiddify.com'
HIDDIFY_IOS_URL = 'https://apps.apple.com/us/app/hiddify-proxy-vpn/id6596777532'


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='👤 Мой профиль'), KeyboardButton(text='💳 Купить подписку')],
            [KeyboardButton(text='📱 Приложения'), KeyboardButton(text='❓ Помощь')],
        ],
        resize_keyboard=True,
    )


def plans_keyboard(plans: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for plan in plans:
        text = f"{plan['emoji']} {plan['title']} | {plan['price_rub']} RUB | {plan['duration_days']} дн"
        rows.append([InlineKeyboardButton(text=text, callback_data=f"buy:{plan['id']}")])
    rows.append([InlineKeyboardButton(text='⬅ В главное меню', callback_data='menu:main')])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def protocol_keyboard(plan_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text='VLESS', callback_data=f'buy:{plan_id}:vless'),
                InlineKeyboardButton(text='Hysteria', callback_data=f'buy:{plan_id}:hysteria'),
            ],
            [InlineKeyboardButton(text='⬅ Назад', callback_data='menu:plans')],
        ]
    )


def apps_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text='Windows: v2rayN', url=V2RAYN_RELEASES_URL)],
            [InlineKeyboardButton(text='Android: NekoBox', url=NEKOBOX_RELEASES_URL)],
            [InlineKeyboardButton(text='Android/iPhone/PC: Hiddify', url=HIDDIFY_DOWNLOAD_URL)],
            [InlineKeyboardButton(text='Google Play: Hiddify', url=HIDDIFY_ANDROID_URL)],
            [InlineKeyboardButton(text='App Store: Hiddify', url=HIDDIFY_IOS_URL)],
        ]
    )


def checkout_keyboard(order_id: str, confirmation_url: str | None) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if confirmation_url:
        rows.append([InlineKeyboardButton(text='💳 Оплатить', url=confirmation_url)])
    rows.append([InlineKeyboardButton(text='🔄 Проверить оплату', callback_data=f'check:{order_id}')])
    rows.append([InlineKeyboardButton(text='⬅ Назад', callback_data='menu:plans')])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def profile_actions_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text='⬅ В главное меню', callback_data='menu:main')],
        ]
    )
