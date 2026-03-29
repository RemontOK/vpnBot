# VPN Bot + YooKassa

Отдельный проект Telegram-бота для продажи VPN-подписок через Marzban с приемом оплаты через ЮKassa.

## Что уже реализовано (MVP)
- Telegram-бот (aiogram) с красивыми кнопками и emoji
- Выбор тарифа из базы
- Создание платежа в ЮKassa
- Кнопка оплаты + кнопка проверки оплаты
- API (FastAPI) + PostgreSQL
- Автоматическая выдача VPN-подписки через Marzban API после оплаты
- Webhook endpoint для ЮKassa: `/api/webhooks/yookassa`

## Структура
- `bot/` — Telegram bot
- `api/` — backend API
- `infra/` — Dockerfiles
- `docker-compose.yml` — запуск всего проекта

## Быстрый старт
1. Перейди в каталог проекта:
```bash
cd vpn-bot-yookassa
```

2. Создай env:
```bash
cp .env.example .env
```

3. Заполни `.env`:
- `TELEGRAM_BOT_TOKEN`
- `YOOKASSA_SHOP_ID`
- `YOOKASSA_SECRET_KEY`
- `YOOKASSA_RETURN_URL`
- `MARZBAN_*`

4. Запусти сервисы:
```bash
docker compose up -d --build
```

5. Проверь API:
```bash
curl http://localhost:8080/api/health
```

## Настройка YooKassa webhook
В личном кабинете ЮKassa укажи URL:
`https://YOUR_DOMAIN/api/webhooks/yookassa`

Нужен внешний HTTPS-домен, доступный из интернета.

## Подключение к реальному Marzban
По умолчанию включен mock режим:
```env
MARZBAN_USE_MOCK=true
```

Для реального подключения:
```env
MARZBAN_USE_MOCK=false
MARZBAN_BASE_URL=http://YOUR_SERVER:8000
MARZBAN_USERNAME=...
MARZBAN_PASSWORD=...
MARZBAN_DEFAULT_PROTOCOL=vless
MARZBAN_DEFAULT_INBOUND_TAG=VLESS TCP
```

## Команды бота
- `/start` — меню
- `/plans` — выбор тарифа
- `/help` — помощь
- `/support` — контакты поддержки

## Важно по безопасности
- Никогда не публикуй токены/секреты
- Если токен попал в чат, сразу перевыпусти его
- Для прода используй reverse-proxy (Caddy/Nginx) + HTTPS
