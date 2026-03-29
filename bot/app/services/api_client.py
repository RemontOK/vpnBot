import httpx

from ..config import settings


class BackendClient:
    def __init__(self) -> None:
        self.base_url = settings.api_base_url.rstrip('/')

    async def get_plans(self) -> list[dict]:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(f'{self.base_url}/api/plans')
            response.raise_for_status()
            return response.json()

    async def create_order(self, telegram_id: int, username: str | None, first_name: str | None, plan_id: int) -> dict:
        payload = {
            'telegram_id': telegram_id,
            'username': username,
            'first_name': first_name,
            'plan_id': plan_id,
        }
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(f'{self.base_url}/api/orders', json=payload)
            if response.status_code == 409:
                raise httpx.HTTPStatusError('Subscription already active', request=response.request, response=response)
            response.raise_for_status()
            return response.json()

    async def get_order(self, order_id: str) -> dict:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(f'{self.base_url}/api/orders/{order_id}')
            response.raise_for_status()
            return response.json()

    async def get_profile(self, telegram_id: int) -> dict:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(f'{self.base_url}/api/profile/{telegram_id}')
            response.raise_for_status()
            return response.json()
