"""Pruebas de persistencia y orquestación."""

from __future__ import annotations

from pathlib import Path

from database import DatabaseManager
from services.demo_api_server import build_assets, build_users, build_weather
from transformers import merge_results, transform_assets, transform_users, transform_weather


def test_bulk_insert_carga_mas_de_cien_registros(tmp_path: Path) -> None:
    """Valida que la carga masiva inserte más de 100 registros normalizados."""
    database = DatabaseManager(tmp_path / "test.db")
    database.initialize_schema(reset=True)

    result = merge_results(
        [
            transform_users(build_users(limit=20)),
            transform_assets(build_assets(limit=20)),
            transform_weather(build_weather(limit=20)),
        ]
    )
    counters = database.load_all(result.records, result.errors)
    counts = database.table_counts()

    assert counters["users"] == 20
    assert counters["asset_price_history"] == 100
    assert counters["weather_forecasts"] == 60
    assert sum(counts.values()) > 100
