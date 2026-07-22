"""Servicio Adapter para la API financiera."""

from __future__ import annotations

from api_client import APIClient


class FinanceService:
    """Encapsula el endpoint de activos financieros."""

    def __init__(self, client: APIClient) -> None:
        self.client = client

    def fetch_assets(self, limit: int, chaos: bool = False, empty: bool = False) -> dict:
        """Obtiene activos financieros desde el proveedor externo."""
        return self.client.get(
            "/api/v1/finance/assets",
            params={"limit": limit, "chaos": str(chaos).lower(), "empty": str(empty).lower()},
        )
