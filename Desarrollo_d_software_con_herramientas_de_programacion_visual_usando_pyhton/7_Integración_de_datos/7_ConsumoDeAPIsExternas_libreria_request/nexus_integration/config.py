"""Environment-based configuration for the integration project."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Tuple

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - project still works without dotenv
    load_dotenv = None


if load_dotenv:
    load_dotenv()


def _get_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_float_tuple(
    connect_name: str,
    read_name: str,
    default_connect: float,
    default_read: float,
) -> Tuple[float, float]:
    connect = float(os.getenv(connect_name, str(default_connect)))
    read = float(os.getenv(read_name, str(default_read)))
    return connect, read


@dataclass(frozen=True)
class Settings:
    """Typed application settings loaded from environment variables."""

    demo_provider_enabled: bool = _get_bool("DEMO_PROVIDER_ENABLED", True)
    demo_provider_host: str = os.getenv("DEMO_PROVIDER_HOST", "127.0.0.1")
    demo_provider_port: int = int(os.getenv("DEMO_PROVIDER_PORT", "8765"))

    chaos_mode: bool = _get_bool("CHAOS_MODE", False)
    database_name: str = os.getenv("DATABASE_NAME", "nexus_data.db")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    weather_base_url: str = os.getenv("WEATHER_BASE_URL", "")
    fleet_base_url: str = os.getenv("FLEET_BASE_URL", "")
    identity_base_url: str = os.getenv("IDENTITY_BASE_URL", "")

    weather_api_key: str = os.getenv("WEATHER_API_KEY", "")
    fleet_bearer_token: str = os.getenv("FLEET_BEARER_TOKEN", "")
    identity_api_key: str = os.getenv("IDENTITY_API_KEY", "")

    timeout: Tuple[float, float] = _get_float_tuple(
        "REQUEST_CONNECT_TIMEOUT_SECONDS",
        "REQUEST_READ_TIMEOUT_SECONDS",
        3.05,
        10.0,
    )
    max_retries: int = int(os.getenv("MAX_RETRIES", "3"))
    backoff_factor: float = float(os.getenv("BACKOFF_FACTOR", "0.5"))
    jitter_seconds: float = float(os.getenv("JITTER_SECONDS", "0.25"))
    cache_ttl_seconds: int = int(os.getenv("CACHE_TTL_SECONDS", "300"))
    rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))

    vehicle_ids: str = os.getenv("VEHICLE_IDS", "V-1001,V-1002,V-1003")
    driver_ids: str = os.getenv("DRIVER_IDS", "D-1001,D-1002,D-1003")

    @property
    def demo_base_url(self) -> str:
        return f"http://{self.demo_provider_host}:{self.demo_provider_port}"

    def resolve_base_url(self, configured: str) -> str:
        if configured:
            return configured.rstrip("/")
        if self.demo_provider_enabled:
            return self.demo_base_url
        raise ValueError("Base URL is required when demo provider is disabled.")


def load_settings() -> Settings:
    """Return a fresh settings snapshot."""

    return Settings()
