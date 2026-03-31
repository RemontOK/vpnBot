# VPN Bot + YooKassa

Telegram bot for selling VPN subscriptions through YooKassa with automatic account provisioning in Marzban.

## Features

- Telegram bot on aiogram
- FastAPI backend
- PostgreSQL storage
- YooKassa payment flow
- Manual payment check button
- Automatic Marzban user creation after payment
- Old-style compatibility links for `VLESS WS TLS`
- Built-in HTTPS reverse proxy for `/pac{hash}/sub` and `/ws{hash}`

## Project structure

- `bot/` - Telegram bot
- `api/` - backend API
- `infra/` - Dockerfiles
- `docker-compose.yml` - app + proxy stack

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
- `VLESS_COMPAT_*`

3. Start services:

```bash
docker compose up -d --build
```

4. Check API:

```bash
curl http://localhost:8080/api/health
```

5. Check proxy:

```bash
curl -k https://localhost/healthz
```

## YooKassa webhook

Set this URL in YooKassa:

```text
https://YOUR_DOMAIN/api/webhooks/yookassa
```

The bundled `proxy` service can expose this path on `443`.

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

For old-style VLESS WS TLS links, point Marzban/Xray to a plain WS inbound and let the local `proxy` terminate TLS:

```env
MARZBAN_USE_MOCK=false
MARZBAN_VLESS_PROTOCOL=vless
MARZBAN_VLESS_INBOUND_TAG=VLESS WS TLS
VLESS_COMPAT_DOMAIN=YOUR_DOMAIN
VLESS_COMPAT_PORT=443
VLESS_COMPAT_PATH=/ws{hash}
VLESS_COMPAT_SUB_PATH=/pac{hash}/sub
VLESS_COMPAT_SNI=YOUR_DOMAIN
VLESS_COMPAT_SECURITY=tls
PROXY_WS_UPSTREAM_HOST=host.docker.internal
PROXY_WS_UPSTREAM_PORT=8444
```

If `/certs/tls.crt` and `/certs/tls.key` are absent, the proxy generates a self-signed certificate at startup. For production, mount real files into `infra/proxy/certs/`.

## Bot flow

1. User chooses a plan.
2. Bot creates a payment.
3. After payment confirmation, backend creates the Marzban user and stores its UUID.
4. API returns compatibility links:
   - `vless://...type=ws...path=/ws{hash}`
   - `https://DOMAIN/pac{hash}/sub?id=UUID`
5. `proxy` serves both routes on `443`.

## Security notes

- Do not commit bot tokens or YooKassa secrets unless you explicitly accept the risk.
- Rotate secrets immediately if they were exposed.
- Use HTTPS for production webhook and panel URLs.
