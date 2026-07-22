"""Small helper to inspect SQLite counts."""

from __future__ import annotations

from config import load_settings
from database import NexusRepository


def main() -> None:
    settings = load_settings()
    repo = NexusRepository(settings.database_name)
    repo.initialize_schema()
    print(f"Base: {settings.database_name}")
    for table in ["drivers", "vehicle_positions", "weather_snapshots", "sync_runs"]:
        print(f"- {table}: {repo.count_rows(table)} registros")
    repo.close()


if __name__ == "__main__":
    main()
