"""Identity provider adapter."""

from __future__ import annotations

from typing import Optional

import requests

from api_client import APIClient
from config import Settings
from models import DriverIdentity


class IdentityService(APIClient):
    """Adapter for the external driver identity provider."""

    def __init__(
        self,
        base_url: str,
        settings: Settings,
        session: Optional[requests.Session] = None,
    ) -> None:
        headers = {}
        if settings.identity_api_key:
            headers["X-Identity-Key"] = settings.identity_api_key
        super().__init__(
            base_url=base_url,
            service_name="identity",
            default_headers=headers,
            timeout=settings.timeout,
            max_retries=settings.max_retries,
            backoff_factor=settings.backoff_factor,
            jitter_seconds=settings.jitter_seconds,
            cache_ttl_seconds=settings.cache_ttl_seconds,
            rate_limit_per_minute=settings.rate_limit_per_minute,
            session=session,
        )

    def verify_driver(self, driver_id: str) -> DriverIdentity:
        """Verify a driver using a POST JSON payload."""

        payload = self.post(
            "/identity/verify",
            payload={"driver_id": driver_id},
            use_cache=True,
            cache_ttl_seconds=900,
        )
        return DriverIdentity.from_provider(payload)
