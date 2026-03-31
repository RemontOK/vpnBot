import random
import string
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin

import httpx

from ..config import settings


class MarzbanClient:
    def __init__(self) -> None:
        self._token: str | None = None

    async def create_user(
        self, telegram_id: int, duration_days: int, data_limit_gb: int, protocol: str
    ) -> dict:
        if settings.legacy_vpn_issuer_url:
            return await self._create_legacy_user(telegram_id)

        if settings.marzban_use_mock:
            username = self._username(telegram_id)
            return {
                "username": username,
                "subscription_url": f"https://example.com/sub/{username}",
                "protocol": protocol,
            }

        token = await self._get_token()
        username = self._username(telegram_id)
        expire_ts = int(
            (datetime.now(timezone.utc) + timedelta(days=duration_days)).timestamp()
        )

        marzban_protocol, inbound_tag = self._resolve_protocol(protocol)

        payload = {
            "username": username,
            "status": "active",
            "expire": expire_ts,
            "data_limit": data_limit_gb * 1024 * 1024 * 1024,
            "data_limit_reset_strategy": "no_reset",
            "proxies": {marzban_protocol: {}},
            "inbounds": {marzban_protocol: [inbound_tag]},
        }

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"{settings.marzban_base_url}/api/user",
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
            data = response.json()

        sub_url = data.get("subscription_url") or settings.marzban_sub_fallback
        if sub_url and sub_url.startswith("/"):
            public_base = settings.marzban_public_base_url or settings.marzban_base_url
            sub_url = urljoin(f"{public_base}/", sub_url.lstrip("/"))
        return {"username": username, "subscription_url": sub_url, "protocol": protocol}

    async def get_user(self, username: str) -> dict | None:
        if settings.legacy_vpn_issuer_url:
            return await self._get_legacy_user(username)

        if settings.marzban_use_mock:
            return {"username": username, "status": "active"}

        token = await self._get_token()
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                f"{settings.marzban_base_url}/api/user/{username}",
                headers={"Authorization": f"Bearer {token}"},
            )

        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

    async def _get_token(self) -> str:
        if self._token:
            return self._token

        data = {
            "username": settings.marzban_username,
            "password": settings.marzban_password,
        }
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"{settings.marzban_base_url}/api/admin/token", data=data
            )
            response.raise_for_status()
            token = response.json().get("access_token")

        if not token:
            raise RuntimeError("Marzban token is empty")

        self._token = token
        return token

    @staticmethod
    def _username(telegram_id: int) -> str:
        suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
        return f"tg{telegram_id}_{suffix}"

    def _resolve_protocol(self, protocol: str) -> tuple[str, str]:
        normalized = (protocol or "").strip().lower()
        if normalized == "hysteria":
            return (
                settings.marzban_hysteria_protocol,
                settings.marzban_hysteria_inbound_tag,
            )
        return settings.marzban_vless_protocol, settings.marzban_vless_inbound_tag

    async def _create_legacy_user(self, telegram_id: int) -> dict:
        username = f"tg{telegram_id}"
        headers = self._legacy_headers()
        payload = {"email": username}
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                settings.legacy_vpn_issuer_url.rstrip("/") + "/legacy-api/issue-vless",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()

        return {
            "username": username,
            "subscription_url": data["subscription_url"],
            "protocol": "vless",
            "vless_url": data.get("vless_url"),
        }

    async def _get_legacy_user(self, username: str) -> dict | None:
        headers = self._legacy_headers()
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                settings.legacy_vpn_issuer_url.rstrip("/") + "/legacy-api/client",
                params={"email": username},
                headers=headers,
            )

        if response.status_code == 404:
            return None
        response.raise_for_status()
        data = response.json()
        return {
            "username": data["email"],
            "status": "disabled" if data.get("is_disabled") else "active",
            "subscription_url": data.get("subscription_url"),
            "vless_url": data.get("vless_url"),
        }

    def _legacy_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if settings.legacy_vpn_issuer_token:
            headers["X-Legacy-Api-Token"] = settings.legacy_vpn_issuer_token
        return headers
