from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_name: str = 'VPN Bot API'
    app_env: str = 'dev'
    api_host: str = '0.0.0.0'
    api_port: int = 8080

    postgres_user: str = 'vpn'
    postgres_password: str = 'vpnpass'
    postgres_db: str = 'vpn_bot'
    postgres_host: str = 'postgres'
    postgres_port: int = 5432

    yookassa_shop_id: str = ''
    yookassa_secret_key: str = ''
    yookassa_return_url: str = 'https://t.me/your_bot'

    marzban_base_url: str = 'http://127.0.0.1:8000'
    marzban_public_base_url: str = 'http://127.0.0.1:8000'
    marzban_username: str = 'admin'
    marzban_password: str = 'admin'
    marzban_use_mock: bool = True

    marzban_default_protocol: str = 'vless'
    marzban_default_inbound_tag: str = 'VLESS TCP'
    marzban_vless_protocol: str = 'vless'
    marzban_vless_inbound_tag: str = 'VLESS TCP'
    marzban_hysteria_protocol: str = 'hysteria2'
    marzban_hysteria_inbound_tag: str = 'HYSTERIA 2'
    marzban_sub_fallback: str = ''

    plan_starter_price: int = 199
    plan_starter_days: int = 30
    plan_starter_gb: int = 100

    plan_pro_price: int = 399
    plan_pro_days: int = 30
    plan_pro_gb: int = 300

    plan_ultra_price: int = 699
    plan_ultra_days: int = 90
    plan_ultra_gb: int = 1000

    @property
    def database_url(self) -> str:
        return (
            f'postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}'
            f'@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}'
        )


settings = Settings()

