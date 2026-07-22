from __future__ import annotations

import argparse

from config.settings import settings
from repositories.data_manager import DataManager


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inicializa la base SQLite de PokéData Lab."
    )
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Carga datos locales de demostración si la base está vacía.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Elimina la base actual antes de crear el esquema.",
    )
    args = parser.parse_args()

    if args.reset and settings.database_path.exists():
        settings.database_path.unlink()
        print(f"Base eliminada: {settings.database_path}")

    manager = DataManager(settings.database_path)
    manager.initialize_database()
    print(f"Base inicializada: {settings.database_path}")

    if args.seed:
        inserted = manager.seed_sample_data()
        print(f"Pokémon demo insertados: {inserted}")

    print(f"Total de Pokémon: {manager.count_pokemon()}")


if __name__ == "__main__":
    main()
