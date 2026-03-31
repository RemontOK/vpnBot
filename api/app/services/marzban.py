import random
import re
import string
from datetime import datetime, timedelta, timezone
from urllib.parse import quote, urljoin

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
            uuid = "00000000-0000-4000-8000-000000000000"
            return {
                "username": username,
                "uuid": uuid,
                "subscription_url": f"https://example.com/sub/{username}",
                "compat_subscription_url": self.build_compat_subscription_url(uuid),
                "vless_url": self.build_compat_vless_url(uuid, username),
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

        return self._normalize_marzban_user(
            data=data,
            fallback_username=username,
            protocol=protocol,
        )

    async def get_user(self, username: str) -> dict | None:
        if settings.legacy_vpn_issuer_url:
            return await self._get_legacy_user(username)

        if settings.marzban_use_mock:
            uuid = "00000000-0000-4000-8000-000000000000"
            return {
                "username": username,
                "uuid": uuid,
                "status": "active",
                "subscription_url": f"https://example.com/sub/{username}",
                "compat_subscription_url": self.build_compat_subscription_url(uuid),
                "vless_url": self.build_compat_vless_url(uuid, username),
            }

        token = await self._get_token()
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                f"{settings.marzban_base_url}/api/user/{username}",
                headers={"Authorization": f"Bearer {token}"},
            )

        if response.status_code == 404:
            return None
        response.raise_for_status()
        return self._normalize_marzban_user(
            data=response.json(),
            fallback_username=username,
            protocol="vless",
        )

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
            "uuid": data.get("uuid"),
            "subscription_url": data["subscription_url"],
            "compat_subscription_url": data["subscription_url"],
            "protocol": "vless",
            "vless_url": data.get("vless_url"),
        }

    async def _get_legacy_user(self, username: str) -> dict | None:
        username = self._legacy_username(username)
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
            "uuid": data.get("uuid"),
            "status": "disabled" if data.get("is_disabled") else "active",
            "subscription_url": data.get("subscription_url"),
            "compat_subscription_url": data.get("subscription_url"),
            "vless_url": data.get("vless_url"),
        }

    def _legacy_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if settings.legacy_vpn_issuer_token:
            headers["X-Legacy-Api-Token"] = settings.legacy_vpn_issuer_token
        return headers

    def build_compat_subscription_url(self, uuid: str | None) -> str | None:
        if not uuid:
            return None
        sub_path = settings.vless_compat_sub_path.format(hash=settings.compat_hash)
        return (
            f"{settings.compat_sub_scheme}://{settings.compat_domain}"
            f"{sub_path}?id={uuid}"
        )

    def build_compat_vless_url(
        self, uuid: str | None, username: str | None
    ) -> str | None:
        if not uuid:
            return None
        path = settings.vless_compat_path.format(hash=settings.compat_hash)
        return (
            f"vless://{uuid}@{settings.compat_domain}:{settings.vless_compat_port}"
            f"?flow="
            f"&path={quote(path, safe='')}"
            f"&security={settings.vless_compat_security}"
            f"&sni={settings.compat_sni}"
            f"&fp={settings.vless_compat_fp}"
            f"&type={settings.vless_compat_type}"
            f"#{username or uuid}"
        )

    def _normalize_marzban_user(
        self, data: dict, fallback_username: str, protocol: str
    ) -> dict:
        username = data.get("username") or fallback_username
        uuid = self._extract_vless_uuid(data)
        sub_url = data.get("subscription_url") or settings.marzban_sub_fallback
        if sub_url and sub_url.startswith("/"):
            public_base = settings.marzban_public_base_url or settings.marzban_base_url
            sub_url = urljoin(f"{public_base}/", sub_url.lstrip("/"))

        return {
            "username": username,
            "uuid": uuid,
            "status": data.get("status", "active"),
            "subscription_url": sub_url,
            "compat_subscription_url": self.build_compat_subscription_url(uuid)
            or sub_url,
            "protocol": protocol,
            "vless_url": self.build_compat_vless_url(uuid, username),
        }

    @staticmethod
    def _extract_vless_uuid(data: dict) -> str | None:
        proxies = data.get("proxies")
        if isinstance(proxies, dict):
            for key in ("vless", "VLESS"):
                proxy = proxies.get(key)
                if isinstance(proxy, dict):
                    for field in ("id", "uuid"):
                        value = proxy.get(field)
                        if value:
                            return str(value)

        links = data.get("links")
        if isinstance(links, list):
            for link in links:
                if isinstance(link, str):
                    match = re.match(r"^vless://([^@]+)@", link)
                    if match:
                        return match.group(1)

        for key in ("subscription_url", "link"):
            value = data.get(key)
            if isinstance(value, str) and value.startswith("vless://"):
                match = re.match(r"^vless://([^@]+)@", value)
                if match:
                    return match.group(1)

        return None

    @staticmethod
    def _legacy_username(username: str) -> str:
        match = re.match(r"^(tg\d+)", username or "")
        if match:
            return match.group(1)
        return username
