from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Mapping, Sequence

import pandas as pd

from models.pokemon import Pokemon
from utils.date_utils import utc_now_iso
from utils.exceptions import DataValidationError


class DataManager:
    """Gestiona esquema, transacciones, persistencia y consultas SQLite."""

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
        CREATE TABLE IF NOT EXISTS pokemon (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            base_experience INTEGER,
            height_dm INTEGER NOT NULL CHECK (height_dm > 0),
            weight_hg INTEGER NOT NULL CHECK (weight_hg > 0),
            image_url TEXT,
            generation INTEGER NOT NULL CHECK (generation BETWEEN 1 AND 9),
            abilities TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS types (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS pokemon_types (
            pokemon_id INTEGER NOT NULL,
            type_id INTEGER NOT NULL,
            slot INTEGER NOT NULL CHECK (slot > 0),
            PRIMARY KEY (pokemon_id, type_id),
            FOREIGN KEY (pokemon_id) REFERENCES pokemon(id)
                ON UPDATE CASCADE ON DELETE CASCADE,
            FOREIGN KEY (type_id) REFERENCES types(id)
                ON UPDATE CASCADE ON DELETE RESTRICT
        );

        CREATE TABLE IF NOT EXISTS pokemon_stats (
            pokemon_id INTEGER NOT NULL,
            stat_name TEXT NOT NULL,
            base_stat INTEGER NOT NULL CHECK (base_stat >= 0),
            PRIMARY KEY (pokemon_id, stat_name),
            FOREIGN KEY (pokemon_id) REFERENCES pokemon(id)
                ON UPDATE CASCADE ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS sync_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            status TEXT NOT NULL,
            requested_records INTEGER NOT NULL DEFAULT 0,
            valid_records INTEGER NOT NULL DEFAULT 0,
            inserted_records INTEGER NOT NULL DEFAULT 0,
            updated_records INTEGER NOT NULL DEFAULT 0,
            failed_resources INTEGER NOT NULL DEFAULT 0,
            message TEXT,
            synced_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_pokemon_generation
            ON pokemon (generation);
        CREATE INDEX IF NOT EXISTS idx_pokemon_types_type
            ON pokemon_types (type_id, pokemon_id);
        CREATE INDEX IF NOT EXISTS idx_pokemon_stats_name
            ON pokemon_stats (stat_name, base_stat DESC);
        """
        with self._connect() as connection:
            connection.executescript(schema)

    def save_pokemon_batch(
        self,
        raw_items: Sequence[Mapping[str, Any]],
    ) -> dict[str, Any]:
        valid_pokemon: list[Pokemon] = []
        validation_errors: list[str] = []

        for raw_item in raw_items:
            try:
                valid_pokemon.append(Pokemon.from_api(raw_item))
            except (DataValidationError, TypeError, ValueError) as exc:
                validation_errors.append(str(exc))

        if not valid_pokemon:
            detail = "; ".join(validation_errors[:3])
            raise DataValidationError(
                f"No hubo registros válidos para guardar. {detail}"
            )

        pokemon_ids = [pokemon.id for pokemon in valid_pokemon]
        placeholders = ", ".join("?" for _ in pokemon_ids)
        now = utc_now_iso()

        with self._connect() as connection:
            existing_rows = connection.execute(
                f"SELECT id FROM pokemon WHERE id IN ({placeholders});",
                pokemon_ids,
            ).fetchall()
            existing_ids = {int(row["id"]) for row in existing_rows}

            for pokemon in valid_pokemon:
                connection.execute(
                    """
                    INSERT INTO pokemon (
                        id, name, base_experience, height_dm, weight_hg,
                        image_url, generation, abilities, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        name = excluded.name,
                        base_experience = excluded.base_experience,
                        height_dm = excluded.height_dm,
                        weight_hg = excluded.weight_hg,
                        image_url = excluded.image_url,
                        generation = excluded.generation,
                        abilities = excluded.abilities,
                        updated_at = excluded.updated_at;
                    """,
                    (
                        pokemon.id,
                        pokemon.name,
                        pokemon.base_experience,
                        pokemon.height_dm,
                        pokemon.weight_hg,
                        pokemon.image_url,
                        pokemon.generation,
                        ", ".join(pokemon.abilities),
                        now,
                        now,
                    ),
                )

                connection.execute(
                    "DELETE FROM pokemon_types WHERE pokemon_id = ?;",
                    (pokemon.id,),
                )
                for slot, type_name in pokemon.types:
                    connection.execute(
                        "INSERT OR IGNORE INTO types (name) VALUES (?);",
                        (type_name,),
                    )
                    type_id = connection.execute(
                        "SELECT id FROM types WHERE name = ?;",
                        (type_name,),
                    ).fetchone()["id"]
                    connection.execute(
                        """
                        INSERT INTO pokemon_types (pokemon_id, type_id, slot)
                        VALUES (?, ?, ?);
                        """,
                        (pokemon.id, type_id, slot),
                    )

                connection.execute(
                    "DELETE FROM pokemon_stats WHERE pokemon_id = ?;",
                    (pokemon.id,),
                )
                connection.executemany(
                    """
                    INSERT INTO pokemon_stats (pokemon_id, stat_name, base_stat)
                    VALUES (?, ?, ?);
                    """,
                    [
                        (pokemon.id, stat_name, base_stat)
                        for stat_name, base_stat in pokemon.stats.items()
                    ],
                )

        inserted_records = sum(
            1 for pokemon in valid_pokemon if pokemon.id not in existing_ids
        )
        updated_records = len(valid_pokemon) - inserted_records
        return {
            "requested_records": len(raw_items),
            "valid_records": len(valid_pokemon),
            "inserted_records": inserted_records,
            "updated_records": updated_records,
            "validation_errors": validation_errors,
        }

    def log_sync(
        self,
        status: str,
        requested_records: int = 0,
        valid_records: int = 0,
        inserted_records: int = 0,
        updated_records: int = 0,
        failed_resources: int = 0,
        message: str | None = None,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO sync_log (
                    status, requested_records, valid_records,
                    inserted_records, updated_records, failed_resources,
                    message, synced_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    status,
                    requested_records,
                    valid_records,
                    inserted_records,
                    updated_records,
                    failed_resources,
                    message,
                    utc_now_iso(),
                ),
            )

    def get_pokemon_data(self) -> pd.DataFrame:
        query = """
        SELECT
            p.id,
            p.name,
            p.base_experience,
            p.height_dm,
            p.weight_hg,
            p.image_url,
            p.generation,
            p.abilities,
            p.created_at,
            p.updated_at,
            GROUP_CONCAT(DISTINCT t.name) AS types,
            MAX(CASE WHEN ps.stat_name = 'hp' THEN ps.base_stat END) AS hp,
            MAX(CASE WHEN ps.stat_name = 'attack' THEN ps.base_stat END) AS attack,
            MAX(CASE WHEN ps.stat_name = 'defense' THEN ps.base_stat END) AS defense,
            MAX(CASE WHEN ps.stat_name = 'special-attack' THEN ps.base_stat END)
                AS special_attack,
            MAX(CASE WHEN ps.stat_name = 'special-defense' THEN ps.base_stat END)
                AS special_defense,
            MAX(CASE WHEN ps.stat_name = 'speed' THEN ps.base_stat END) AS speed
        FROM pokemon AS p
        LEFT JOIN pokemon_types AS pt ON pt.pokemon_id = p.id
        LEFT JOIN types AS t ON t.id = pt.type_id
        LEFT JOIN pokemon_stats AS ps ON ps.pokemon_id = p.id
        GROUP BY p.id
        ORDER BY p.id;
        """
        with self._connect() as connection:
            dataframe = pd.read_sql_query(query, connection)

        if dataframe.empty:
            return dataframe

        numeric_columns = [
            "id",
            "base_experience",
            "height_dm",
            "weight_hg",
            "generation",
            "hp",
            "attack",
            "defense",
            "special_attack",
            "special_defense",
            "speed",
        ]
        for column in numeric_columns:
            dataframe[column] = pd.to_numeric(dataframe[column], errors="coerce")

        dataframe["types"] = dataframe["types"].fillna("")
        return dataframe

    def get_types(self) -> list[str]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT name FROM types ORDER BY name;"
            ).fetchall()
        return [str(row["name"]) for row in rows]

    def get_last_sync(self) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM sync_log ORDER BY id DESC LIMIT 1;"
            ).fetchone()
        return dict(row) if row else None

    def count_pokemon(self) -> int:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS total FROM pokemon;"
            ).fetchone()
        return int(row["total"])

    def seed_sample_data(self) -> int:
        if self.count_pokemon() > 0:
            return 0
        result = self.save_pokemon_batch(_build_demo_payloads())
        self.log_sync(
            status="DEMO",
            requested_records=result["requested_records"],
            valid_records=result["valid_records"],
            inserted_records=result["inserted_records"],
            message="Datos locales de demostración cargados.",
        )
        return int(result["inserted_records"])


def _build_demo_payloads() -> list[dict[str, Any]]:
    """Crea datos offline con la misma forma JSON usada por PokéAPI."""

    rows = [
        (1, "bulbasaur", 64, 7, 69, ("grass", "poison"), (45, 49, 49, 65, 65, 45)),
        (2, "ivysaur", 142, 10, 130, ("grass", "poison"), (60, 62, 63, 80, 80, 60)),
        (3, "venusaur", 263, 20, 1000, ("grass", "poison"), (80, 82, 83, 100, 100, 80)),
        (4, "charmander", 62, 6, 85, ("fire",), (39, 52, 43, 60, 50, 65)),
        (5, "charmeleon", 142, 11, 190, ("fire",), (58, 64, 58, 80, 65, 80)),
        (6, "charizard", 267, 17, 905, ("fire", "flying"), (78, 84, 78, 109, 85, 100)),
        (7, "squirtle", 63, 5, 90, ("water",), (44, 48, 65, 50, 64, 43)),
        (8, "wartortle", 142, 10, 225, ("water",), (59, 63, 80, 65, 80, 58)),
        (9, "blastoise", 265, 16, 855, ("water",), (79, 83, 100, 85, 105, 78)),
        (25, "pikachu", 112, 4, 60, ("electric",), (35, 55, 40, 50, 50, 90)),
        (26, "raichu", 243, 8, 300, ("electric",), (60, 90, 55, 90, 80, 110)),
        (39, "jigglypuff", 95, 5, 55, ("normal", "fairy"), (115, 45, 20, 45, 25, 20)),
        (52, "meowth", 58, 4, 42, ("normal",), (40, 45, 35, 40, 40, 90)),
        (54, "psyduck", 64, 8, 196, ("water",), (50, 52, 48, 65, 50, 55)),
        (66, "machop", 61, 8, 195, ("fighting",), (70, 80, 50, 35, 35, 35)),
        (74, "geodude", 60, 4, 200, ("rock", "ground"), (40, 80, 100, 30, 30, 20)),
        (92, "gastly", 62, 13, 1, ("ghost", "poison"), (30, 35, 30, 100, 35, 80)),
        (133, "eevee", 65, 3, 65, ("normal",), (55, 55, 50, 45, 65, 55)),
        (143, "snorlax", 189, 21, 4600, ("normal",), (160, 110, 65, 65, 110, 30)),
        (149, "dragonite", 300, 22, 2100, ("dragon", "flying"), (91, 134, 95, 100, 100, 80)),
        (150, "mewtwo", 340, 20, 1220, ("psychic",), (106, 110, 90, 154, 90, 130)),
    ]
    stat_names = (
        "hp",
        "attack",
        "defense",
        "special-attack",
        "special-defense",
        "speed",
    )
    payloads: list[dict[str, Any]] = []
    for pokemon_id, name, experience, height, weight, types, stats in rows:
        payloads.append(
            {
                "id": pokemon_id,
                "name": name,
                "base_experience": experience,
                "height": height,
                "weight": weight,
                "abilities": [
                    {"ability": {"name": "demo-ability"}, "is_hidden": False}
                ],
                "types": [
                    {"slot": slot, "type": {"name": type_name}}
                    for slot, type_name in enumerate(types, start=1)
                ],
                "stats": [
                    {"base_stat": value, "effort": 0, "stat": {"name": stat_name}}
                    for stat_name, value in zip(stat_names, stats, strict=True)
                ],
                "sprites": {
                    "front_default": (
                        "https://raw.githubusercontent.com/PokeAPI/sprites/"
                        f"master/sprites/pokemon/{pokemon_id}.png"
                    ),
                    "other": {
                        "official-artwork": {
                            "front_default": (
                                "https://raw.githubusercontent.com/PokeAPI/sprites/"
                                "master/sprites/pokemon/other/official-artwork/"
                                f"{pokemon_id}.png"
                            )
                        }
                    },
                },
            }
        )
    return payloads
