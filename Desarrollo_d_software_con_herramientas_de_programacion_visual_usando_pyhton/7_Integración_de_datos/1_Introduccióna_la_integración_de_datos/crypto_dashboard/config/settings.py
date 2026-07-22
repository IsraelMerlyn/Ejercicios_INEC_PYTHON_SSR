from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    """Configuración central de la aplicación."""

    base_dir: Path
    database_path: Path
    coingecko_base_url: str
    coingecko_api_key: str
    request_timeout_seconds: int
    api_cache_ttl_seconds: int
    minimum_request_interval_seconds: int
    default_currency: str


def load_settings() -> Settings:
    database_name = os.getenv("DATABASE_NAME", "data.db")

    return Settings(
        base_dir=BASE_DIR,
        database_path=BASE_DIR / database_name,
        coingecko_base_url=os.getenv(
            "COINGECKO_BASE_URL",
            "https://api.coingecko.com/api/v3",
        ),
        coingecko_api_key=os.getenv("COINGECKO_API_KEY", "").strip(),
        request_timeout_seconds=int(os.getenv("REQUEST_TIMEOUT_SECONDS", "15")),
        api_cache_ttl_seconds=int(os.getenv("API_CACHE_TTL_SECONDS", "300")),
        minimum_request_interval_seconds=int(
            os.getenv("MINIMUM_REQUEST_INTERVAL_SECONDS", "10")
        ),
        default_currency=os.getenv("DEFAULT_CURRENCY", "usd").lower(),
    )


settings = load_settings()

DEFAULT_COIN_IDS: tuple[str, ...] = (
    "bitcoin",
    "ethereum",
    "solana",
    "cardano",
    "dogecoin",
)

SUPPORTED_CURRENCIES: tuple[str, ...] = ("usd", "mxn", "eur")
