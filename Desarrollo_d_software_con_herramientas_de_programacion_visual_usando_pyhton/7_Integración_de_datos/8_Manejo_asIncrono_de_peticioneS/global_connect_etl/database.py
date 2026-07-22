"""Capa de persistencia SQLite con inserciones masivas."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from models import (
    AddressRecord,
    AssetPriceRecord,
    AssetRecord,
    SubscriptionRecord,
    UserRecord,
    WeatherForecastRecord,
    WeatherLocationRecord,
    WeatherObservationRecord,
)


def utc_now_iso() -> str:
    """Devuelve la fecha actual en UTC usando formato ISO 8601."""
    return datetime.now(timezone.utc).isoformat()


class DatabaseManager:
    """Administra la creación de tablas y las cargas bulk del ETL."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        """Abre una conexión SQLite con claves foráneas habilitadas."""
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize_schema(self, reset: bool = False) -> None:
        """Crea el esquema relacional y reinicia la base si se solicita."""
        if reset and self.database_path.exists():
            self.database_path.unlink()

        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    external_id TEXT PRIMARY KEY,
                    full_name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL,
                    created_at_utc TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS addresses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_external_id TEXT NOT NULL UNIQUE,
                    city TEXT NOT NULL,
                    country TEXT NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    FOREIGN KEY (user_external_id) REFERENCES users(external_id)
                );

                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_external_id TEXT NOT NULL,
                    plan_name TEXT NOT NULL,
                    price_usd NUMERIC NOT NULL,
                    active INTEGER NOT NULL,
                    started_at_utc TEXT NOT NULL,
                    FOREIGN KEY (user_external_id) REFERENCES users(external_id),
                    UNIQUE(user_external_id, plan_name, started_at_utc)
                );

                CREATE TABLE IF NOT EXISTS financial_assets (
                    external_id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    sector TEXT NOT NULL,
                    currency TEXT NOT NULL,
                    listed_at_utc TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS asset_price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    asset_external_id TEXT NOT NULL,
                    price_usd NUMERIC NOT NULL,
                    volume NUMERIC NOT NULL,
                    recorded_at_utc TEXT NOT NULL,
                    FOREIGN KEY (asset_external_id) REFERENCES financial_assets(external_id),
                    UNIQUE(asset_external_id, recorded_at_utc)
                );

                CREATE TABLE IF NOT EXISTS weather_locations (
                    external_id TEXT PRIMARY KEY,
                    city TEXT NOT NULL,
                    country TEXT NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS weather_observations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    location_external_id TEXT NOT NULL,
                    temperature_c REAL NOT NULL,
                    humidity INTEGER NOT NULL,
                    condition TEXT NOT NULL,
                    observed_at_utc TEXT NOT NULL,
                    FOREIGN KEY (location_external_id) REFERENCES weather_locations(external_id),
                    UNIQUE(location_external_id, observed_at_utc)
                );

                CREATE TABLE IF NOT EXISTS weather_forecasts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    location_external_id TEXT NOT NULL,
                    forecast_date TEXT NOT NULL,
                    min_temp_c REAL NOT NULL,
                    max_temp_c REAL NOT NULL,
                    rain_probability REAL NOT NULL,
                    FOREIGN KEY (location_external_id) REFERENCES weather_locations(external_id),
                    UNIQUE(location_external_id, forecast_date)
                );

                CREATE TABLE IF NOT EXISTS etl_errors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    external_id TEXT NOT NULL,
                    error_type TEXT NOT NULL,
                    message TEXT NOT NULL,
                    raw_payload TEXT NOT NULL,
                    created_at_utc TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS etl_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at_utc TEXT NOT NULL,
                    finished_at_utc TEXT NOT NULL,
                    total_processed INTEGER NOT NULL,
                    total_success INTEGER NOT NULL,
                    total_failed INTEGER NOT NULL,
                    elapsed_seconds REAL NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_asset_prices_asset_time
                    ON asset_price_history(asset_external_id, recorded_at_utc);

                CREATE INDEX IF NOT EXISTS idx_weather_observations_location_time
                    ON weather_observations(location_external_id, observed_at_utc);
                """
            )

    def load_all(self, records: dict[str, list[Any]], errors: list[dict[str, str]]) -> dict[str, int]:
        """Carga todos los registros transformados usando bulk inserts."""
        counters: dict[str, int] = {}
        with self.connect() as connection:
            counters["users"] = self._insert_users(connection, records.get("users", []))
            counters["addresses"] = self._insert_addresses(connection, records.get("addresses", []))
            counters["subscriptions"] = self._insert_subscriptions(
                connection, records.get("subscriptions", [])
            )
            counters["financial_assets"] = self._insert_assets(
                connection, records.get("assets", [])
            )
            counters["asset_price_history"] = self._insert_asset_prices(
                connection, records.get("asset_prices", [])
            )
            counters["weather_locations"] = self._insert_weather_locations(
                connection, records.get("weather_locations", [])
            )
            counters["weather_observations"] = self._insert_weather_observations(
                connection, records.get("weather_observations", [])
            )
            counters["weather_forecasts"] = self._insert_weather_forecasts(
                connection, records.get("weather_forecasts", [])
            )
            counters["etl_errors"] = self._insert_errors(connection, errors)
        return counters

    def record_run(
        self,
        started_at_utc: str,
        finished_at_utc: str,
        total_processed: int,
        total_success: int,
        total_failed: int,
        elapsed_seconds: float,
    ) -> None:
        """Guarda el resumen final de ejecución del ETL."""
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO etl_runs (
                    started_at_utc, finished_at_utc, total_processed,
                    total_success, total_failed, elapsed_seconds
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    started_at_utc,
                    finished_at_utc,
                    total_processed,
                    total_success,
                    total_failed,
                    elapsed_seconds,
                ),
            )

    def table_counts(self) -> dict[str, int]:
        """Cuenta registros por tabla para inspección rápida."""
        tables = [
            "users",
            "addresses",
            "subscriptions",
            "financial_assets",
            "asset_price_history",
            "weather_locations",
            "weather_observations",
            "weather_forecasts",
            "etl_errors",
            "etl_runs",
        ]
        with self.connect() as connection:
            return {
                table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
                for table in tables
            }

    def _insert_users(self, connection: sqlite3.Connection, rows: list[UserRecord]) -> int:
        data = [
            (
                row.external_id,
                row.full_name,
                row.email,
                row.status,
                row.created_at_utc.isoformat(),
            )
            for row in rows
        ]
        connection.executemany(
            """
            INSERT INTO users (external_id, full_name, email, status, created_at_utc)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(external_id) DO UPDATE SET
                full_name=excluded.full_name,
                email=excluded.email,
                status=excluded.status,
                created_at_utc=excluded.created_at_utc
            """,
            data,
        )
        return len(data)

    def _insert_addresses(self, connection: sqlite3.Connection, rows: list[AddressRecord]) -> int:
        data = [tuple(asdict(row).values()) for row in rows]
        connection.executemany(
            """
            INSERT INTO addresses (user_external_id, city, country, latitude, longitude)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_external_id) DO UPDATE SET
                city=excluded.city,
                country=excluded.country,
                latitude=excluded.latitude,
                longitude=excluded.longitude
            """,
            data,
        )
        return len(data)

    def _insert_subscriptions(
        self, connection: sqlite3.Connection, rows: list[SubscriptionRecord]
    ) -> int:
        data = [
            (
                row.user_external_id,
                row.plan_name,
                float(row.price_usd),
                1 if row.active else 0,
                row.started_at_utc.isoformat(),
            )
            for row in rows
        ]
        connection.executemany(
            """
            INSERT OR IGNORE INTO subscriptions (
                user_external_id, plan_name, price_usd, active, started_at_utc
            ) VALUES (?, ?, ?, ?, ?)
            """,
            data,
        )
        return len(data)

    def _insert_assets(self, connection: sqlite3.Connection, rows: list[AssetRecord]) -> int:
        data = [
            (
                row.external_id,
                row.symbol,
                row.name,
                row.sector,
                row.currency,
                row.listed_at_utc.isoformat(),
            )
            for row in rows
        ]
        connection.executemany(
            """
            INSERT INTO financial_assets (
                external_id, symbol, name, sector, currency, listed_at_utc
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(external_id) DO UPDATE SET
                symbol=excluded.symbol,
                name=excluded.name,
                sector=excluded.sector,
                currency=excluded.currency,
                listed_at_utc=excluded.listed_at_utc
            """,
            data,
        )
        return len(data)

    def _insert_asset_prices(
        self, connection: sqlite3.Connection, rows: list[AssetPriceRecord]
    ) -> int:
        data = [
            (
                row.asset_external_id,
                float(row.price_usd),
                float(row.volume),
                row.recorded_at_utc.isoformat(),
            )
            for row in rows
        ]
        connection.executemany(
            """
            INSERT OR IGNORE INTO asset_price_history (
                asset_external_id, price_usd, volume, recorded_at_utc
            ) VALUES (?, ?, ?, ?)
            """,
            data,
        )
        return len(data)

    def _insert_weather_locations(
        self, connection: sqlite3.Connection, rows: list[WeatherLocationRecord]
    ) -> int:
        data = [tuple(asdict(row).values()) for row in rows]
        connection.executemany(
            """
            INSERT INTO weather_locations (external_id, city, country, latitude, longitude)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(external_id) DO UPDATE SET
                city=excluded.city,
                country=excluded.country,
                latitude=excluded.latitude,
                longitude=excluded.longitude
            """,
            data,
        )
        return len(data)

    def _insert_weather_observations(
        self, connection: sqlite3.Connection, rows: list[WeatherObservationRecord]
    ) -> int:
        data = [
            (
                row.location_external_id,
                row.temperature_c,
                row.humidity,
                row.condition,
                row.observed_at_utc.isoformat(),
            )
            for row in rows
        ]
        connection.executemany(
            """
            INSERT OR IGNORE INTO weather_observations (
                location_external_id, temperature_c, humidity, condition, observed_at_utc
            ) VALUES (?, ?, ?, ?, ?)
            """,
            data,
        )
        return len(data)

    def _insert_weather_forecasts(
        self, connection: sqlite3.Connection, rows: list[WeatherForecastRecord]
    ) -> int:
        data = [tuple(asdict(row).values()) for row in rows]
        connection.executemany(
            """
            INSERT OR IGNORE INTO weather_forecasts (
                location_external_id, forecast_date, min_temp_c, max_temp_c, rain_probability
            ) VALUES (?, ?, ?, ?, ?)
            """,
            data,
        )
        return len(data)

    def _insert_errors(self, connection: sqlite3.Connection, rows: list[dict[str, str]]) -> int:
        data = [
            (
                row["source"],
                row["external_id"],
                row["error_type"],
                row["message"],
                row["raw_payload"],
                utc_now_iso(),
            )
            for row in rows
        ]
        connection.executemany(
            """
            INSERT INTO etl_errors (
                source, external_id, error_type, message, raw_payload, created_at_utc
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            data,
        )
        return len(data)
