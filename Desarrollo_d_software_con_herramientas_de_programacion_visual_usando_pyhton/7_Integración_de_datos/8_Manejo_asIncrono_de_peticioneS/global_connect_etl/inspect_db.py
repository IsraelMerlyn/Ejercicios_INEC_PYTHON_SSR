"""Script de inspección rápida para la base SQLite."""

from __future__ import annotations

from config import settings
from database import DatabaseManager


def main() -> None:
    """Imprime conteos de registros por tabla."""
    database = DatabaseManager(settings.database_path)
    if not settings.database_path.exists():
        print(f"No existe la base: {settings.database_path}")
        print("Ejecuta primero: python main.py --reset-db")
        return

    print(f"Base SQLite: {settings.database_path}")
    print("\nConteo de tablas:")
    for table, count in database.table_counts().items():
        print(f"- {table}: {count}")


if __name__ == "__main__":
    main()
