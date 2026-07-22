"""Exportación opcional a CSV para análisis externo."""

from __future__ import annotations

import csv
from pathlib import Path

from config import settings
from database import DatabaseManager


def export_table(table_name: str, output_dir: Path) -> int:
    """Exporta una tabla completa a un archivo CSV."""
    database = DatabaseManager(settings.database_path)
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / f"{table_name}.csv"

    with database.connect() as connection:
        rows = connection.execute(f"SELECT * FROM {table_name}").fetchall()
        if not rows:
            output_path.write_text("", encoding="utf-8")
            return 0

        with output_path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(dict(row) for row in rows)
    return len(rows)


def main() -> None:
    """Exporta las tablas principales de negocio."""
    tables = [
        "users",
        "subscriptions",
        "financial_assets",
        "asset_price_history",
        "weather_locations",
        "weather_observations",
        "weather_forecasts",
    ]
    output_dir = Path("exports")
    for table in tables:
        count = export_table(table, output_dir)
        print(f"{table}: {count} registros exportados")


if __name__ == "__main__":
    main()
