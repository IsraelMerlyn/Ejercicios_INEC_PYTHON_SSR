"""Pruebas de transformación de JSON anidado."""

from __future__ import annotations

from datetime import timezone

import pytest

from exceptions import DataValidationError
from models import parse_datetime, parse_decimal
from services.demo_api_server import build_assets, build_users, build_weather
from transformers import transform_assets, transform_users, transform_weather


def test_parse_datetime_normaliza_utc() -> None:
    """Valida que una fecha ISO 8601 se convierta a UTC."""
    parsed = parse_datetime("2026-07-21T12:00:00-06:00", "created_at")

    assert parsed.tzinfo is not None
    assert parsed.astimezone(timezone.utc).hour == 18


def test_parse_decimal_rechaza_valor_invalido() -> None:
    """Valida que un precio inválido no entre al pipeline."""
    with pytest.raises(DataValidationError):
        parse_decimal("N/A", "price_usd")


def test_transform_assets_mapea_historial_profundo() -> None:
    """Valida el mapeo data -> attributes -> history -> values."""
    payload = build_assets(limit=2)
    result = transform_assets(payload)

    assert len(result.records["assets"]) == 2
    assert len(result.records["asset_prices"]) == 10
    assert result.errors == []


def test_transform_users_registra_error_sin_romper() -> None:
    """Valida que un registro corrupto se mande al log de errores."""
    payload = build_users(limit=2)
    payload["data"][0]["profile"].pop("email")

    result = transform_users(payload)

    assert len(result.records["users"]) == 1
    assert len(result.errors) == 1
    assert result.errors[0]["source"] == "users"


def test_transform_weather_genera_observaciones_y_forecasts() -> None:
    """Valida que clima se normalice en tres estructuras."""
    payload = build_weather(limit=3)
    result = transform_weather(payload)

    assert len(result.records["weather_locations"]) == 3
    assert len(result.records["weather_observations"]) == 3
    assert len(result.records["weather_forecasts"]) == 9
