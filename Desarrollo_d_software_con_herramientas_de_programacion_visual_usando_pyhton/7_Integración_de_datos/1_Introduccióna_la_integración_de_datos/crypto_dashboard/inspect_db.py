from __future__ import annotations

import sqlite3

from config.settings import settings


def main() -> None:
    if not settings.database_path.exists():
        print("La base todavía no existe. Ejecuta: python init_db.py --seed")
        return

    with sqlite3.connect(settings.database_path) as connection:
        connection.row_factory = sqlite3.Row
        tables = connection.execute(
            """
            SELECT name
            FROM sqlite_master
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

        print("\nÚltimos 5 precios:")
        rows = connection.execute(
            """
            SELECT a.name, ph.current_price, ph.currency, ph.recorded_at
            FROM price_history ph
            INNER JOIN assets a ON a.id = ph.asset_id
            ORDER BY ph.recorded_at DESC, a.market_cap_rank
            LIMIT 5;
            """
        ).fetchall()

        for row in rows:
            print(
                f"  {row['name']}: {row['current_price']:.6f} "
                f"{row['currency'].upper()} | {row['recorded_at']}"
            )


if __name__ == "__main__":
    main()
