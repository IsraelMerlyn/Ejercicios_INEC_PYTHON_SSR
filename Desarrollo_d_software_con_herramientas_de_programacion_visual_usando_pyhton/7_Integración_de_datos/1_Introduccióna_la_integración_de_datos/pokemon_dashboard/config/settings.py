from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True, slots=True)
class Settings:
    """Configuración centralizada de la aplicación."""

    base_dir: Path
    database_path: Path
    pokeapi_base_url: str
    request_timeout_seconds: int
    api_cache_ttl_seconds: int
    minimum_request_interval_seconds: float


def load_settings() -> Settings:
    database_name = os.getenv("DATABASE_NAME", "data.db")

    return Settings(
        base_dir=BASE_DIR,
        database_path=BASE_DIR / database_name,
        pokeapi_base_url=os.getenv(
            "POKEAPI_BASE_URL",
            "https://pokeapi.co/api/v2",
        ).rstrip("/"),
        request_timeout_seconds=int(os.getenv("REQUEST_TIMEOUT_SECONDS", "20")),
        api_cache_ttl_seconds=int(os.getenv("API_CACHE_TTL_SECONDS", "3600")),
        minimum_request_interval_seconds=float(
            os.getenv("MINIMUM_REQUEST_INTERVAL_SECONDS", "0.10")
        ),
    )


settings = load_settings()

STAT_NAMES: tuple[str, ...] = (
    "hp",
    "attack",
    "defense",
    "special-attack",
    "special-defense",
    "speed",
)
