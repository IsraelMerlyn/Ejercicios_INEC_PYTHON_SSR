from __future__ import annotations

import sqlite3

from config.settings import settings


def main() -> None:
    if not settings.database_path.exists():
        print("La base no existe. Ejecuta: python init_db.py --seed")
        return

    with sqlite3.connect(settings.database_path) as connection:
        connection.row_factory = sqlite3.Row
        tables = connection.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name;
            """
        ).fetchall()

        print(f"Base: {settings.database_path}")
        print("Tablas:")
        for table in tables:
            table_name = table["name"]
            total = connection.execute(
                f'SELECT COUNT(*) AS total FROM "{table_name}"'
            ).fetchone()["total"]
            print(f"  - {table_name}: {total} registros")

        print("\nPrimeros 10 Pokémon:")
        rows = connection.execute(
            """
            SELECT id, name, base_experience, generation
            FROM pokemon ORDER BY id LIMIT 10;
            """
        ).fetchall()
        for row in rows:
            print(
                f"  #{row['id']:03d} {row['name']} | "
                f"EXP {row['base_experience']} | Gen {row['generation']}"
            )


if __name__ == "__main__":
    main()
