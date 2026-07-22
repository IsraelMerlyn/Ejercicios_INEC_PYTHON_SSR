"""SQLite persistence for the Nexus integration pipeline."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

from models import DriverIdentity, FleetPosition, WeatherSnapshot


class NexusRepository:
    """Small repository layer around SQLite using parameterized queries."""

    def __init__(self, database_path: str = "nexus_data.db") -> None:
        self.database_path = Path(database_path)
        self.connection = sqlite3.connect(self.database_path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON;")

    def initialize_schema(self) -> None:
        """Create all tables and indexes required by the exercise."""

        with self.connection:
            self.connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS drivers (
                    driver_id TEXT PRIMARY KEY,
                    full_name TEXT NOT NULL,
                    license_status TEXT NOT NULL,
                    verified INTEGER NOT NULL,
                    risk_score REAL NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS vehicle_positions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vehicle_id TEXT NOT NULL,
                    driver_id TEXT NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    speed_kmh REAL NOT NULL,
                    status TEXT NOT NULL,
                    captured_at TEXT NOT NULL,
                    FOREIGN KEY (driver_id) REFERENCES drivers(driver_id)
                        ON UPDATE CASCADE
                );

                CREATE TABLE IF NOT EXISTS weather_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    city TEXT NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    temperature_c REAL NOT NULL,
                    condition TEXT NOT NULL,
                    observed_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS sync_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at TEXT NOT NULL,
                    finished_at TEXT NOT NULL,
                    processed INTEGER NOT NULL,
                    failed INTEGER NOT NULL,
                    skipped INTEGER NOT NULL,
                    notes TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_vehicle_positions_vehicle
                    ON vehicle_positions(vehicle_id, captured_at);
                CREATE INDEX IF NOT EXISTS idx_weather_coordinates
                    ON weather_snapshots(latitude, longitude, observed_at);
                """
            )

    def save_driver(self, driver: DriverIdentity) -> None:
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO drivers (
                    driver_id,
                    full_name,
                    license_status,
                    verified,
                    risk_score,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(driver_id) DO UPDATE SET
                    full_name = excluded.full_name,
                    license_status = excluded.license_status,
                    verified = excluded.verified,
                    risk_score = excluded.risk_score,
                    updated_at = excluded.updated_at;
                """,
                (
                    driver.driver_id,
                    driver.full_name,
                    driver.license_status,
                    int(driver.verified),
                    driver.risk_score,
                    driver.updated_at.isoformat(),
                ),
            )

    def save_position(self, position: FleetPosition) -> None:
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO vehicle_positions (
                    vehicle_id,
                    driver_id,
                    latitude,
                    longitude,
                    speed_kmh,
                    status,
                    captured_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    position.vehicle_id,
                    position.driver_id,
                    position.latitude,
                    position.longitude,
                    position.speed_kmh,
                    position.status,
                    position.captured_at.isoformat(),
                ),
            )

    def save_weather(self, weather: WeatherSnapshot) -> None:
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO weather_snapshots (
                    city,
                    latitude,
                    longitude,
                    temperature_c,
                    condition,
                    observed_at
                ) VALUES (?, ?, ?, ?, ?, ?);
                """,
                (
                    weather.city,
                    weather.latitude,
                    weather.longitude,
                    weather.temperature_c,
                    weather.condition,
                    weather.observed_at.isoformat(),
                ),
            )

    def save_sync_run(
        self,
        started_at: str,
        finished_at: str,
        processed: int,
        failed: int,
        skipped: int,
        notes: Optional[str] = None,
    ) -> None:
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO sync_runs (
                    started_at,
                    finished_at,
                    processed,
                    failed,
                    skipped,
                    notes
                ) VALUES (?, ?, ?, ?, ?, ?);
                """,
                (started_at, finished_at, processed, failed, skipped, notes),
            )

    def count_rows(self, table_name: str) -> int:
        if table_name not in {
            "drivers",
            "vehicle_positions",
            "weather_snapshots",
            "sync_runs",
        }:
            raise ValueError("Unsupported table")
        cursor = self.connection.execute(f"SELECT COUNT(*) AS total FROM {table_name}")
        return int(cursor.fetchone()["total"])

    def close(self) -> None:
        self.connection.close()
