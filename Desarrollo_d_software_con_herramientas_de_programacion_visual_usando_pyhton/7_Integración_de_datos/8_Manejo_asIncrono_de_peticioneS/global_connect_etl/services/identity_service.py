"""Servicio Adapter para la API de usuarios."""

from __future__ import annotations

from api_client import APIClient


class IdentityService:
    """Encapsula el endpoint de identidad de usuarios."""

    def __init__(self, client: APIClient) -> None:
        self.client = client

    def fetch_users(self, limit: int, chaos: bool = False, empty: bool = False) -> dict:
        """Obtiene usuarios desde el proveedor externo."""
        return self.client.get(
            "/api/v1/users",
            params={"limit": limit, "chaos": str(chaos).lower(), "empty": str(empty).lower()},
        )
