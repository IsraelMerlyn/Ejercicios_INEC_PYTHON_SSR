"""Internal models and transformation functions for provider responses."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from exceptions import DataValidationError, InvalidResponseFormat

LOGGER = logging.getLogger("integration.models")


def parse_datetime(value: Any, field_name: str) -> datetime:
    """Parse ISO 8601 strings or epoch timestamps into timezone-aware datetimes."""

    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)

    if isinstance(value, str) and value.strip():
        normalized = value.strip().replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError as exc:
            raise DataValidationError(
                f"Invalid datetime value for {field_name}: {value!r}"
            ) from exc

    raise DataValidationError(f"Missing datetime value for {field_name}")


def required_string(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key)
    if value is None or str(value).strip() == "":
        raise DataValidationError(f"Missing required string field: {key}")
    return str(value).strip()


def optional_string(value: Any, default: str = "unknown") -> str:
    if value is None or str(value).strip() == "":
        return default
    return str(value).strip()


def to_float(value: Any, field_name: str, required: bool = True) -> Optional[float]:
    if value in {None, "", "N/A", "NA", "null"}:
        if required:
            raise DataValidationError(f"Missing numeric field: {field_name}")
        LOGGER.warning("non_critical_numeric_missing field=%s value=%r", field_name, value)
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        if required:
            raise DataValidationError(
                f"Invalid numeric value for {field_name}: {value!r}"
            ) from exc
        LOGGER.warning("non_critical_numeric_invalid field=%s value=%r", field_name, value)
        return None


def get_nested(payload: Mapping[str, Any], *keys: str) -> Any:
    current: Any = payload
    for key in keys:
        if not isinstance(current, Mapping) or key not in current:
            raise InvalidResponseFormat("Missing nested field: " + ".".join(keys))
        current = current[key]
    return current


@dataclass(frozen=True)
class DriverIdentity:
    """Stable internal representation for driver identity data."""

    driver_id: str
    full_name: str
    license_status: str
    verified: bool
    risk_score: float
    updated_at: datetime

    @classmethod
    def from_provider(cls, payload: Mapping[str, Any]) -> "DriverIdentity":
        profile = get_nested(payload, "profile")
        compliance = get_nested(payload, "compliance")
        driver_id = required_string(payload, "driverId")
        full_name = required_string(profile, "fullName").title()
        license_status = required_string(compliance, "licenseStatus").lower()
        risk_score = to_float(compliance.get("riskScore", 0), "riskScore", required=False)
        return cls(
            driver_id=driver_id,
            full_name=full_name,
            license_status=license_status,
            verified=bool(compliance.get("verified", False)),
            risk_score=risk_score if risk_score is not None else 0.0,
            updated_at=parse_datetime(payload.get("updatedAt"), "updatedAt"),
        )


@dataclass(frozen=True)
class FleetPosition:
    """Stable internal representation for real-time fleet tracking data."""

    vehicle_id: str
    driver_id: str
    latitude: float
    longitude: float
    speed_kmh: float
    status: str
    captured_at: datetime

    @classmethod
    def from_provider(cls, payload: Mapping[str, Any]) -> "FleetPosition":
        coordinates = get_nested(payload, "location", "coordinates")
        vehicle_id = required_string(payload, "vehicleId")
        driver_id = required_string(payload, "driverId")
        latitude = to_float(coordinates.get("lat"), "location.coordinates.lat")
        longitude = to_float(coordinates.get("lon"), "location.coordinates.lon")
        speed = to_float(payload.get("speedKmh", 0), "speedKmh", required=False)
        return cls(
            vehicle_id=vehicle_id,
            driver_id=driver_id,
            latitude=latitude if latitude is not None else 0.0,
            longitude=longitude if longitude is not None else 0.0,
            speed_kmh=speed if speed is not None else 0.0,
            status=optional_string(payload.get("status"), default="unknown").lower(),
            captured_at=parse_datetime(payload.get("capturedAt"), "capturedAt"),
        )


@dataclass(frozen=True)
class WeatherSnapshot:
    """Stable internal representation for weather data at a fleet position."""

    city: str
    latitude: float
    longitude: float
    temperature_c: float
    condition: str
    observed_at: datetime

    @classmethod
    def from_provider(cls, payload: Mapping[str, Any]) -> "WeatherSnapshot":
        location = get_nested(payload, "location")
        measurements = get_nested(payload, "measurements")
        latitude = to_float(location.get("lat"), "location.lat")
        longitude = to_float(location.get("lon"), "location.lon")
        temperature = to_float(measurements.get("temp_celsius"), "measurements.temp_celsius")
        return cls(
            city=optional_string(location.get("city"), default="unknown").title(),
            latitude=latitude if latitude is not None else 0.0,
            longitude=longitude if longitude is not None else 0.0,
            temperature_c=temperature if temperature is not None else 0.0,
            condition=optional_string(measurements.get("condition"), default="unknown").lower(),
            observed_at=parse_datetime(payload.get("observedAt"), "observedAt"),
        )


@dataclass
class SyncReport:
    """Execution summary generated by the orchestrator."""

    processed: int = 0
    failed: int = 0
    skipped: int = 0

    def register_success(self) -> None:
        self.processed += 1

    def register_failure(self) -> None:
        self.failed += 1

    def register_skip(self) -> None:
        self.skipped += 1

    @property
    def total(self) -> int:
        return self.processed + self.failed + self.skipped
