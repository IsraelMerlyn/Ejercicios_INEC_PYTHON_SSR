"""Modelos intermedios estables para desacoplar el JSON externo."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from exceptions import DataValidationError


def parse_datetime(value: str | None, field_name: str) -> datetime:
    """Convierte fechas ISO 8601 a datetime normalizado en UTC."""
    if not value:
        raise DataValidationError(f"El campo obligatorio {field_name} viene vacío")
    try:
        cleaned = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(cleaned)
    except ValueError as exc:
        raise DataValidationError(f"El campo {field_name} no tiene formato ISO 8601 válido") from exc

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def parse_decimal(value: Any, field_name: str) -> Decimal:
    """Convierte strings numéricos a Decimal para evitar errores de precisión."""
    if value in (None, "", "N/A"):
        raise DataValidationError(f"El campo obligatorio {field_name} no tiene valor numérico")
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise DataValidationError(f"El campo {field_name} no se puede convertir a decimal") from exc


def parse_float(value: Any, field_name: str) -> float:
    """Convierte valores a float validando nulos y cadenas inválidas."""
    if value in (None, "", "N/A"):
        raise DataValidationError(f"El campo obligatorio {field_name} no tiene valor numérico")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise DataValidationError(f"El campo {field_name} no se puede convertir a float") from exc


@dataclass(frozen=True)
class UserRecord:
    """Usuario normalizado para la tabla users."""

    external_id: str
    full_name: str
    email: str
    status: str
    created_at_utc: datetime


@dataclass(frozen=True)
class AddressRecord:
    """Dirección normalizada relacionada con un usuario."""

    user_external_id: str
    city: str
    country: str
    latitude: float
    longitude: float


@dataclass(frozen=True)
class SubscriptionRecord:
    """Suscripción normalizada relacionada con un usuario."""

    user_external_id: str
    plan_name: str
    price_usd: Decimal
    active: bool
    started_at_utc: datetime


@dataclass(frozen=True)
class AssetRecord:
    """Activo financiero normalizado."""

    external_id: str
    symbol: str
    name: str
    sector: str
    currency: str
    listed_at_utc: datetime


@dataclass(frozen=True)
class AssetPriceRecord:
    """Registro histórico de precio para un activo."""

    asset_external_id: str
    price_usd: Decimal
    volume: Decimal
    recorded_at_utc: datetime


@dataclass(frozen=True)
class WeatherLocationRecord:
    """Ubicación climática normalizada."""

    external_id: str
    city: str
    country: str
    latitude: float
    longitude: float


@dataclass(frozen=True)
class WeatherObservationRecord:
    """Observación climática actual de una ciudad."""

    location_external_id: str
    temperature_c: float
    humidity: int
    condition: str
    observed_at_utc: datetime


@dataclass(frozen=True)
class WeatherForecastRecord:
    """Pronóstico climático diario normalizado."""

    location_external_id: str
    forecast_date: str
    min_temp_c: float
    max_temp_c: float
    rain_probability: float
