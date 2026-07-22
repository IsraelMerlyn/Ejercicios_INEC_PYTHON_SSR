"""Configuración central del proyecto Global-Connect."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - solo aplica si no se instaló python-dotenv
    load_dotenv = None

BASE_DIR = Path(__file__).resolve().parent

if load_dotenv:
    load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    """Valores de configuración leídos desde variables de entorno."""

    base_url: str = os.getenv("GLOBAL_CONNECT_BASE_URL", "http://127.0.0.1:8765")
    database_name: str = os.getenv("DATABASE_NAME", "global_connect.db")
    bearer_token: str = os.getenv("GLOBAL_CONNECT_BEARER_TOKEN", "demo-token")
    api_key: str = os.getenv("GLOBAL_CONNECT_API_KEY", "demo-api-key")
    request_timeout: float = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "10"))
    max_retries: int = int(os.getenv("MAX_RETRIES", "3"))
    backoff_base_seconds: float = float(os.getenv("BACKOFF_BASE_SECONDS", "0.20"))
    cache_ttl_seconds: int = int(os.getenv("CACHE_TTL_SECONDS", "60"))
    demo_server_enabled: bool = os.getenv("USE_DEMO_SERVER", "true").lower() == "true"
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    @property
    def database_path(self) -> Path:
        """Devuelve la ruta absoluta del archivo SQLite."""
        return BASE_DIR / self.database_name


settings = Settings()
