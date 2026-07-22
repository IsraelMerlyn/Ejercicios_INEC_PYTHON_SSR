"""Fleet tracking provider adapter."""

from __future__ import annotations

from typing import Optional

import requests

from api_client import APIClient
from config import Settings
from models import FleetPosition


class FleetService(APIClient):
    """Adapter for real-time vehicle location data."""

    def __init__(
        self,
        base_url: str,
        settings: Settings,
        session: Optional[requests.Session] = None,
    ) -> None:
        headers = {}
        if settings.fleet_bearer_token:
            headers["Authorization"] = f"Bearer {settings.fleet_bearer_token}"
        super().__init__(
            base_url=base_url,
            service_name="fleet",
            default_headers=headers,
            timeout=settings.timeout,
            max_retries=settings.max_retries,
            backoff_factor=settings.backoff_factor,
            jitter_seconds=settings.jitter_seconds,
            cache_ttl_seconds=5,
            rate_limit_per_minute=settings.rate_limit_per_minute,
            session=session,
        )

    def get_vehicle_position(self, vehicle_id: str) -> FleetPosition:
        """Return the latest known position for a vehicle."""

        payload = self.get(
            f"/fleet/vehicles/{vehicle_id}/location",
            use_cache=True,
            cache_ttl_seconds=3,
        )
        return FleetPosition.from_provider(payload)
