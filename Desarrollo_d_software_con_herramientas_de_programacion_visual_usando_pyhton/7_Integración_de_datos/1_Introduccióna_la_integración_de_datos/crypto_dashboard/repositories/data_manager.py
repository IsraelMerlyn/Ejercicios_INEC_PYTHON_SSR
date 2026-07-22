from __future__ import annotations

import random
import sqlite3
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd

from models.asset import Asset
from models.price_record import PriceRecord
from utils.date_utils import to_sql_datetime


class DataManager:
    """Gestiona el esquema, persistencia y consultas de SQLite."""

    def __init__(self, database_path: Path | str) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON;")
        connection.execute("PRAGMA journal_mode = WAL;")
        return connection

    def initialize_database(self) -> None:
        schema = """
        CREATE TABLE IF NOT EXISTS assets (
            id TEXT PRIMARY KEY,
            symbol TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            image_url TEXT,
            market_cap_rank INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_id TEXT NOT NULL,
            current_price REAL NOT NULL CHECK (current_price > 0),
            market_cap REAL,
            total_volume REAL,
            price_change_percentage_24h REAL,
            high_24h REAL,
            low_24h REAL,
            recorded_at TEXT NOT NULL,
            currency TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (asset_id) REFERENCES assets(id)
                ON UPDATE CASCADE
                ON DELETE RESTRICT,
            UNIQUE (asset_id, recorded_at, currency)
        );

        CREATE TABLE IF NOT EXISTS sync_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            status TEXT NOT NULL,
            received_records INTEGER NOT NULL DEFAULT 0,
            inserted_records INTEGER NOT NULL DEFAULT 0,
            message TEXT,
            synced_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_price_history_asset_date
            ON price_history (asset_id, recorded_at);

        CREATE INDEX IF NOT EXISTS idx_price_history_currency_date
            ON price_history (currency, recorded_at);
        """

        with self._connect() as connection:
            connection.executescript(schema)

    def save_market_snapshot(
        self,
        raw_items: Sequence[Mapping[str, Any]],
        currency: str,
    ) -> dict[str, Any]:
        """Valida, transforma y guarda una respuesta de CoinGecko."""

        assets: list[Asset] = []
        price_records: list[PriceRecord] = []
        validation_errors: list[str] = []

        for raw_item in raw_items:
            try:
                assets.append(Asset.from_api(raw_item))
                price_records.append(PriceRecord.from_api(raw_item, currency))
            except (TypeError, ValueError) as exc:
                validation_errors.append(str(exc))

        if not price_records:
            raise ValueError(
                "No hubo registros válidos para persistir. "
                + "; ".join(validation_errors[:3])
            )

        with self._connect() as connection:
            connection.executemany(
                """
                INSERT INTO assets (
                    id, symbol, name, image_url, market_cap_rank
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    symbol = excluded.symbol,
                    name = excluded.name,
                    image_url = excluded.image_url,
                    market_cap_rank = excluded.market_cap_rank,
                    updated_at = CURRENT_TIMESTAMP;
                """,
                [
                    (
                        asset.id,
                        asset.symbol,
                        asset.name,
                        asset.image_url,
                        asset.market_cap_rank,
                    )
                    for asset in assets
                ],
            )

            before_changes = connection.total_changes
            connection.executemany(
                """
                INSERT OR IGNORE INTO price_history (
                    asset_id,
                    current_price,
                    market_cap,
                    total_volume,
                    price_change_percentage_24h,
                    high_24h,
                    low_24h,
                    recorded_at,
                    currency
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                [
                    (
                        record.asset_id,
                        record.current_price,
                        record.market_cap,
                        record.total_volume,
                        record.price_change_percentage_24h,
                        record.high_24h,
                        record.low_24h,
                        to_sql_datetime(record.recorded_at),
                        record.currency,
                    )
                    for record in price_records
                ],
            )
            inserted_records = connection.total_changes - before_changes

        return {
            "received_records": len(raw_items),
            "valid_records": len(price_records),
            "inserted_records": inserted_records,
            "ignored_duplicates": len(price_records) - inserted_records,
            "validation_errors": validation_errors,
        }

    def log_sync(
        self,
        status: str,
        received_records: int = 0,
        inserted_records: int = 0,
        message: str | None = None,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO sync_log (
                    status, received_records, inserted_records, message
                ) VALUES (?, ?, ?, ?);
                """,
                (status, received_records, inserted_records, message),
            )

    def get_assets(self) -> pd.DataFrame:
        query = """
            SELECT id, symbol, name, image_url, market_cap_rank
            FROM assets
            ORDER BY COALESCE(market_cap_rank, 999999), name;
        """
        with self._connect() as connection:
            return pd.read_sql_query(query, connection)

    def get_history(
        self,
        currency: str = "usd",
        asset_ids: Iterable[str] | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> pd.DataFrame:
        filters = ["ph.currency = ?"]
        parameters: list[Any] = [currency.lower()]

        normalized_asset_ids = tuple(asset_ids or ())
        if normalized_asset_ids:
            placeholders = ", ".join("?" for _ in normalized_asset_ids)
            filters.append(f"ph.asset_id IN ({placeholders})")
            parameters.extend(normalized_asset_ids)

        if start_date:
            start_datetime = datetime.combine(
                start_date,
                time.min,
                tzinfo=timezone.utc,
            )
            filters.append("ph.recorded_at >= ?")
            parameters.append(to_sql_datetime(start_datetime))

        if end_date:
            end_datetime = datetime.combine(
                end_date,
                time.max,
                tzinfo=timezone.utc,
            )
            filters.append("ph.recorded_at <= ?")
            parameters.append(to_sql_datetime(end_datetime))

        where_clause = " AND ".join(filters)
        query = f"""
            SELECT
                ph.id,
                ph.asset_id,
                a.name,
                a.symbol,
                a.image_url,
                a.market_cap_rank,
                ph.current_price,
                ph.market_cap,
                ph.total_volume,
                ph.price_change_percentage_24h,
                ph.high_24h,
                ph.low_24h,
                ph.recorded_at,
                ph.currency
            FROM price_history AS ph
            INNER JOIN assets AS a ON a.id = ph.asset_id
            WHERE {where_clause}
            ORDER BY ph.recorded_at ASC, a.market_cap_rank ASC;
        """

        with self._connect() as connection:
            dataframe = pd.read_sql_query(query, connection, params=parameters)

        if not dataframe.empty:
            dataframe["recorded_at"] = pd.to_datetime(
                dataframe["recorded_at"],
                utc=True,
                errors="coerce",
            )
            numeric_columns = [
                "current_price",
                "market_cap",
                "total_volume",
                "price_change_percentage_24h",
                "high_24h",
                "low_24h",
            ]
            for column in numeric_columns:
                dataframe[column] = pd.to_numeric(
                    dataframe[column],
                    errors="coerce",
                )

        return dataframe

    def get_last_sync(self) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT status, received_records, inserted_records,
                       message, synced_at
                FROM sync_log
                ORDER BY id DESC
                LIMIT 1;
                """
            ).fetchone()

        return dict(row) if row else None

    def count_price_records(self) -> int:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS total FROM price_history;"
            ).fetchone()
        return int(row["total"])

    def seed_sample_data(self) -> int:
        """Carga 15 días de datos reproducibles para ejecutar sin API."""

        self.initialize_database()
        if self.count_price_records() > 0:
            return 0

        randomizer = random.Random(42)
        assets = {
            "bitcoin": {
                "symbol": "btc",
                "name": "Bitcoin",
                "base": 67500.0,
                "rank": 1,
                "market_cap": 1_330_000_000_000,
                "volume": 31_000_000_000,
            },
            "ethereum": {
                "symbol": "eth",
                "name": "Ethereum",
                "base": 3550.0,
                "rank": 2,
                "market_cap": 425_000_000_000,
                "volume": 16_000_000_000,
            },
            "solana": {
                "symbol": "sol",
                "name": "Solana",
                "base": 155.0,
                "rank": 5,
                "market_cap": 75_000_000_000,
                "volume": 3_200_000_000,
            },
            "cardano": {
                "symbol": "ada",
                "name": "Cardano",
                "base": 0.45,
                "rank": 10,
                "market_cap": 16_000_000_000,
                "volume": 420_000_000,
            },
            "dogecoin": {
                "symbol": "doge",
                "name": "Dogecoin",
                "base": 0.14,
                "rank": 8,
                "market_cap": 20_000_000_000,
                "volume": 1_100_000_000,
            },
        }

        inserted_total = 0
        # Tomamos la fecha local de la máquina para no generar un “día futuro”
        # cuando UTC ya cambió de fecha pero el usuario aún está en el día anterior.
        start_date = datetime.now().astimezone().date() - timedelta(days=14)

        for day_index in range(15):
            snapshot_date = start_date + timedelta(days=day_index)
            snapshot_time = datetime.combine(
                snapshot_date,
                time(hour=12),
                tzinfo=timezone.utc,
            )
            raw_items: list[dict[str, Any]] = []

            for asset_id, metadata in assets.items():
                trend = 1 + (day_index * randomizer.uniform(-0.002, 0.006))
                noise = 1 + randomizer.uniform(-0.035, 0.035)
                current_price = max(metadata["base"] * trend * noise, 0.000001)
                change_24h = randomizer.uniform(-6.0, 7.0)

                raw_items.append(
                    {
                        "id": asset_id,
                        "symbol": metadata["symbol"],
                        "name": metadata["name"],
                        "image": None,
                        "market_cap_rank": metadata["rank"],
                        "current_price": current_price,
                        "market_cap": metadata["market_cap"] * trend * noise,
                        "total_volume": metadata["volume"]
                        * randomizer.uniform(0.7, 1.4),
                        "price_change_percentage_24h": change_24h,
                        "high_24h": current_price * randomizer.uniform(1.005, 1.04),
                        "low_24h": current_price * randomizer.uniform(0.96, 0.995),
                        "last_updated": snapshot_time.isoformat().replace(
                            "+00:00", "Z"
                        ),
                    }
                )

            result = self.save_market_snapshot(raw_items, "usd")
            inserted_total += int(result["inserted_records"])

        self.log_sync(
            status="DEMO",
            received_records=inserted_total,
            inserted_records=inserted_total,
            message="Datos de demostración generados localmente.",
        )
        return inserted_total
