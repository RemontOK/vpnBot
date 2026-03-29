# VPN Bot + YooKassa

Telegram bot for selling VPN subscriptions through YooKassa with automatic account provisioning in Marzban.

## Features

- Telegram bot on aiogram
- FastAPI backend
- PostgreSQL storage
- YooKassa payment flow
- Manual payment check button
- Automatic Marzban user creation after payment
- One payment gives access to both `VLESS` and `Hysteria`

## Project structure

- `bot/` - Telegram bot
- `api/` - backend API
- `infra/` - Dockerfiles
- `docker-compose.yml` - local stack

## Quick start

1. Create env file:

```bash
cp .env.example .env
```

2. Fill required values:

- `TELEGRAM_BOT_TOKEN`
- `YOOKASSA_SHOP_ID`
- `YOOKASSA_SECRET_KEY`
- `YOOKASSA_RETURN_URL`
- `MARZBAN_*`

3. Start services:

```bash
docker compose up -d --build
```

4. Check API:

```bash
curl http://localhost:8080/api/health
```

## YooKassa webhook

Set this URL in YooKassa:

```text
https://YOUR_DOMAIN/api/webhooks/yookassa
```

You need public HTTPS access for production webhook delivery.

## Marzban integration

Mock mode is enabled by default:

```env
MARZBAN_USE_MOCK=true
```

For real Marzban:

```env
MARZBAN_USE_MOCK=false
MARZBAN_BASE_URL=http://YOUR_SERVER:8000
MARZBAN_PUBLIC_BASE_URL=https://YOUR_PUBLIC_PANEL
MARZBAN_USERNAME=...
MARZBAN_PASSWORD=...
MARZBAN_VLESS_PROTOCOL=vless
MARZBAN_VLESS_INBOUND_TAG=VLESS TCP
MARZBAN_HYSTERIA_PROTOCOL=hysteria2
MARZBAN_HYSTERIA_INBOUND_TAG=HYSTERIA 2
```

The inbound tag names must match the actual inbound names in your Marzban panel.

## Bot flow

1. User chooses a plan.
2. Bot creates a payment.
3. After payment confirmation, backend creates both Marzban users: `VLESS` and `Hysteria`.
4. User can open profile anytime and copy either link while subscription is active.

## Security notes

- Do not commit bot tokens or YooKassa secrets unless you explicitly accept the risk.
- Rotate secrets immediately if they were exposed.
- Use HTTPS for production webhook and panel URLs.
