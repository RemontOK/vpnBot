import uuid

import httpx

from ..config import settings


class YooKassaClient:
    base_url = 'https://api.yookassa.ru/v3'

    async def create_payment(self, order_id: uuid.UUID, amount_rub: int, description: str) -> dict:
        if not settings.yookassa_shop_id or not settings.yookassa_secret_key:
            raise RuntimeError('YooKassa credentials are empty')

        payload = {
            'amount': {'value': f'{amount_rub:.2f}', 'currency': 'RUB'},
            'capture': True,
            'confirmation': {
                'type': 'redirect',
                'return_url': settings.yookassa_return_url,
            },
            'description': description,
            'metadata': {'order_id': str(order_id)},
        }
        headers = {'Idempotence-Key': str(uuid.uuid4())}

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f'{self.base_url}/payments',
                json=payload,
                auth=(settings.yookassa_shop_id, settings.yookassa_secret_key),
                headers=headers,
            )
            response.raise_for_status()
            return response.json()

    async def get_payment(self, payment_id: str) -> dict:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                f'{self.base_url}/payments/{payment_id}',
                auth=(settings.yookassa_shop_id, settings.yookassa_secret_key),
            )
            response.raise_for_status()
            return response.json()
