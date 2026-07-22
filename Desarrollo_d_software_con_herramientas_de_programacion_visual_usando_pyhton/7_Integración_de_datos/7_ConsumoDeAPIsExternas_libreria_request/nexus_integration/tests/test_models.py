from datetime import datetime

import pytest

from exceptions import DataValidationError
from models import FleetPosition, WeatherSnapshot, parse_datetime


def test_parse_datetime_accepts_iso_8601_zulu():
    parsed = parse_datetime("2026-07-21T18:30:00Z", "capturedAt")

    assert isinstance(parsed, datetime)
    assert parsed.tzinfo is not None
    assert parsed.year == 2026


def test_fleet_position_converts_string_coordinates_to_float():
    position = FleetPosition.from_provider(
        {
            "vehicleId": "V-1001",
            "driverId": "D-1001",
            "location": {"coordinates": {"lat": "19.4326", "lon": "-99.1332"}},
            "speedKmh": "42.5",
            "status": "IN_TRANSIT",
            "capturedAt": "2026-07-21T18:30:00Z",
        }
    )

    assert position.latitude == pytest.approx(19.4326)
    assert position.longitude == pytest.approx(-99.1332)
    assert position.speed_kmh == pytest.approx(42.5)
    assert position.status == "in_transit"


def test_fleet_position_rejects_invalid_critical_coordinate():
    with pytest.raises(DataValidationError):
        FleetPosition.from_provider(
            {
                "vehicleId": "V-1001",
                "driverId": "D-1001",
                "location": {"coordinates": {"lat": "N/A", "lon": "-99.1332"}},
                "speedKmh": "42.5",
                "status": "IN_TRANSIT",
                "capturedAt": "2026-07-21T18:30:00Z",
            }
        )


def test_weather_snapshot_normalizes_text_fields():
    snapshot = WeatherSnapshot.from_provider(
        {
            "location": {"city": "ciudad de mexico", "lat": "19.4326", "lon": "-99.1332"},
            "measurements": {"temp_celsius": "22.4", "condition": "CLEAR"},
            "observedAt": "2026-07-21T18:30:00Z",
        }
    )

    assert snapshot.city == "Ciudad De Mexico"
    assert snapshot.condition == "clear"
