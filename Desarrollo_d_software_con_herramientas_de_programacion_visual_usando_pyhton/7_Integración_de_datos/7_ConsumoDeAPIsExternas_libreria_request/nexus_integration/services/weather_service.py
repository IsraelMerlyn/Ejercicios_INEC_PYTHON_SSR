"""Weather provider adapter."""

from __future__ import annotations

from typing import Optional

import requests

from api_client import APIClient
from config import Settings
from models import WeatherSnapshot


class WeatherService(APIClient):
    """Adapter for weather snapshots by coordinates."""

    def __init__(
        self,
        base_url: str,
        settings: Settings,
        session: Optional[requests.Session] = None,
    ) -> None:
        headers = {}
        if settings.weather_api_key:
            headers["X-API-Key"] = settings.weather_api_key
        super().__init__(
            base_url=base_url,
            service_name="weather",
            default_headers=headers,
            timeout=settings.timeout,
            max_retries=settings.max_retries,
            backoff_factor=settings.backoff_factor,
            jitter_seconds=settings.jitter_seconds,
            cache_ttl_seconds=settings.cache_ttl_seconds,
            rate_limit_per_minute=settings.rate_limit_per_minute,
            session=session,
        )

    def get_current_weather(self, latitude: float, longitude: float) -> WeatherSnapshot:
        """Return a weather snapshot for a coordinate pair."""

        payload = self.get(
            "/weather/current",
            params={"lat": latitude, "lon": longitude},
            use_cache=True,
            cache_ttl_seconds=600,
        )
        return WeatherSnapshot.from_provider(payload)
