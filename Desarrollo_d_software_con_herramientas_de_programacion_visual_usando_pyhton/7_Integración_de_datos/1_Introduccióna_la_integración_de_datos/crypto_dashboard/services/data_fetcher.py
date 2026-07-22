from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from time import monotonic
from typing import Any, Sequence

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from utils.exceptions import (
    ApiAuthenticationError,
    ApiRateLimitError,
    DataSourceConnectionError,
    DataSourceError,
    DataSourceTimeoutError,
)


@dataclass(frozen=True, slots=True)
class FetchResult:
    data: list[dict[str, Any]]
    from_cache: bool
    fetched_at: datetime


@dataclass(slots=True)
class _CacheEntry:
    data: list[dict[str, Any]]
    stored_at_monotonic: float
    fetched_at: datetime


class CoinGeckoClient:
    """Cliente HTTP con timeout, retries, caché y control de frecuencia."""

    def __init__(
        self,
        base_url: str,
        api_key: str = "",
        timeout_seconds: int = 15,
        cache_ttl_seconds: int = 300,
        minimum_request_interval_seconds: int = 10,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key.strip()
        self.timeout_seconds = timeout_seconds
        self.cache_ttl_seconds = cache_ttl_seconds
        self.minimum_request_interval_seconds = minimum_request_interval_seconds
        self._cache: dict[str, _CacheEntry] = {}
        self._last_network_request_at = 0.0
        self._session = self._build_session()

    @staticmethod
    def _build_session() -> requests.Session:
        retry_strategy = Retry(
            total=2,
            connect=2,
            read=2,
            backoff_factor=0.6,
            status_forcelist=(500, 502, 503, 504),
            allowed_methods=frozenset({"GET"}),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session = requests.Session()
        session.mount("https://", adapter)
        session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": "DataViz-Dynamics-Certification-Project/1.0",
            }
        )
        return session

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            return {}
        return {"x-cg-demo-api-key": self.api_key}

    def fetch_markets(
        self,
        coin_ids: Sequence[str],
        currency: str = "usd",
        force_refresh: bool = False,
    ) -> FetchResult:
        normalized_ids = tuple(
            sorted({coin_id.strip().lower() for coin_id in coin_ids if coin_id.strip()})
        )
        if not normalized_ids:
            raise ValueError("Debes proporcionar al menos un coin_id.")

        normalized_currency = currency.strip().lower()
        cache_key = f"{normalized_currency}:{','.join(normalized_ids)}"
        now_monotonic = monotonic()
        cached = self._cache.get(cache_key)

        if cached and not force_refresh:
            cache_age = now_monotonic - cached.stored_at_monotonic
            if cache_age < self.cache_ttl_seconds:
                return FetchResult(
                    data=list(cached.data),
                    from_cache=True,
                    fetched_at=cached.fetched_at,
                )

        elapsed_since_last_request = now_monotonic - self._last_network_request_at
        if (
            self._last_network_request_at > 0
            and elapsed_since_last_request < self.minimum_request_interval_seconds
        ):
            if cached:
                return FetchResult(
                    data=list(cached.data),
                    from_cache=True,
                    fetched_at=cached.fetched_at,
                )
            raise ApiRateLimitError(
                "Protección local activa: espera unos segundos antes de repetir la llamada."
            )

        self._last_network_request_at = now_monotonic
        url = f"{self.base_url}/coins/markets"
        params = {
            "vs_currency": normalized_currency,
            "ids": ",".join(normalized_ids),
            "order": "market_cap_desc",
            "per_page": len(normalized_ids),
            "page": 1,
            "sparkline": "false",
            "price_change_percentage": "24h",
            "locale": "es",
        }

        try:
            response = self._session.get(
                url,
                params=params,
                headers=self._headers(),
                timeout=self.timeout_seconds,
            )
        except requests.Timeout as exc:
            raise DataSourceTimeoutError(
                "CoinGecko no respondió dentro del tiempo esperado."
            ) from exc
        except requests.ConnectionError as exc:
            raise DataSourceConnectionError(
                "No fue posible conectarse con CoinGecko. Verifica tu conexión."
            ) from exc
        except requests.RequestException as exc:
            raise DataSourceError(f"Error HTTP inesperado: {exc}") from exc

        if response.status_code in (401, 403):
            raise ApiAuthenticationError(
                "La API Key Demo es inválida, falta o no tiene permisos."
            )
        if response.status_code == 429:
            raise ApiRateLimitError(
                "CoinGecko rechazó la solicitud por límite de llamadas."
            )

        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise DataSourceError(
                f"CoinGecko respondió HTTP {response.status_code}."
            ) from exc

        try:
            payload = response.json()
        except requests.JSONDecodeError as exc:
            raise DataSourceError("CoinGecko devolvió un JSON inválido.") from exc

        if not isinstance(payload, list):
            raise DataSourceError("La respuesta de CoinGecko no tiene el formato esperado.")

        fetched_at = datetime.now(timezone.utc)
        normalized_payload = [item for item in payload if isinstance(item, dict)]
        self._cache[cache_key] = _CacheEntry(
            data=normalized_payload,
            stored_at_monotonic=monotonic(),
            fetched_at=fetched_at,
        )

        return FetchResult(
            data=list(normalized_payload),
            from_cache=False,
            fetched_at=fetched_at,
        )
