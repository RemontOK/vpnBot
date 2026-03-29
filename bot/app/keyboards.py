from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


V2RAYN_RELEASES_URL = 'https://github.com/2dust/v2rayN/releases/latest'
NEKOBOX_RELEASES_URL = 'https://github.com/MatsuriDayo/NekoBoxForAndroid/releases/latest'
HIDDIFY_DOWNLOAD_URL = 'https://hiddify.com/app/'
HIDDIFY_ANDROID_URL = 'https://play.google.com/store/apps/details?id=app.hiddify.com'
HIDDIFY_IOS_URL = 'https://apps.apple.com/us/app/hiddify-proxy-vpn/id6596777532'


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='\U0001F464 Мой профиль'), KeyboardButton(text='\U0001F4B3 Купить подписку')],
            [KeyboardButton(text='\U0001F4F1 Приложения'), KeyboardButton(text='\u2753 Помощь')],
        ],
        resize_keyboard=True,
    )


def plans_keyboard(plans: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for plan in plans:
        text = f"{plan['emoji']} {plan['title']} | {plan['price_rub']} RUB | {plan['duration_days']} дн"
        rows.append([InlineKeyboardButton(text=text, callback_data=f"buy:{plan['id']}")])
    rows.append([InlineKeyboardButton(text='\U0001F519 В главное меню', callback_data='menu:main')])
    return InlineKeyboardMarkup(inline_keyboard=rows)


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


def demo_checkout_keyboard(order_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text='\U0001F4B3 Оплатить картой', callback_data=f'demo:show:{order_id}')],
            [InlineKeyboardButton(text='\U0001F519 Назад', callback_data='menu:plans')],
        ]
    )


def demo_payment_confirm_keyboard(order_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text='\u2705 Я оплатил', callback_data=f'demo:pay:{order_id}')],
            [InlineKeyboardButton(text='\U0001F50E Проверить оплату', callback_data=f'check:{order_id}')],
        ]
    )


def profile_actions_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text='\U0001F519 В главное меню', callback_data='menu:main')],
        ]
    )
