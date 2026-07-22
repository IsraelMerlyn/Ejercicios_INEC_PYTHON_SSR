"""Servicio Adapter para la API meteorológica."""

from __future__ import annotations

from api_client import APIClient


class WeatherService:
    """Encapsula el endpoint de clima."""

    def __init__(self, client: APIClient) -> None:
        self.client = client

    def fetch_weather(self, limit: int, chaos: bool = False, empty: bool = False) -> dict:
        """Obtiene datos climáticos desde el proveedor externo."""
        return self.client.get(
            "/api/v1/weather/cities",
            params={"limit": limit, "chaos": str(chaos).lower(), "empty": str(empty).lower()},
        )
