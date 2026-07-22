from __future__ import annotations

from typing import Any

import pandas as pd

STAT_COLUMNS = [
    "hp",
    "attack",
    "defense",
    "special_attack",
    "special_defense",
    "speed",
]

METRIC_LABELS: dict[str, str] = {
    "total_stats": "Poder total",
    "attack": "Ataque",
    "defense": "Defensa",
    "special_attack": "Ataque especial",
    "special_defense": "Defensa especial",
    "speed": "Velocidad",
    "base_experience": "Experiencia base",
    "weight_kg": "Peso (kg)",
}


def enrich_pokemon_data(dataframe: pd.DataFrame) -> pd.DataFrame:
    if dataframe.empty:
        return dataframe.copy()

    enriched = dataframe.copy()
    enriched["height_m"] = enriched["height_dm"] / 10
    enriched["weight_kg"] = enriched["weight_hg"] / 10
    enriched["total_stats"] = enriched[STAT_COLUMNS].sum(axis=1)
    enriched["primary_type"] = enriched["types"].str.split(", ").str[0]
    return enriched


def calculate_summary_kpis(dataframe: pd.DataFrame) -> dict[str, Any]:
    if dataframe.empty:
        return {
            "total": 0,
            "average_experience": 0.0,
            "average_weight": 0.0,
            "strongest_name": "N/D",
            "strongest_total": 0,
        }

    strongest = dataframe.sort_values("total_stats", ascending=False).iloc[0]
    return {
        "total": int(len(dataframe)),
        "average_experience": float(dataframe["base_experience"].mean()),
        "average_weight": float(dataframe["weight_kg"].mean()),
        "strongest_name": str(strongest["name"]),
        "strongest_total": int(strongest["total_stats"]),
    }


def calculate_pokemon_kpis(
    dataframe: pd.DataFrame,
    pokemon_id: int,
) -> dict[str, Any]:
    selected = dataframe.loc[dataframe["id"] == pokemon_id]
    if selected.empty:
        raise ValueError(f"No se encontró el Pokémon con id {pokemon_id}.")

    row = selected.iloc[0]
    return {
        "name": row["name"],
        "base_experience": row["base_experience"],
        "height_m": row["height_m"],
        "weight_kg": row["weight_kg"],
        "total_stats": row["total_stats"],
        "types": row["types"],
        "image_url": row["image_url"],
    }


def prepare_ranking(
    dataframe: pd.DataFrame,
    metric: str,
    limit: int = 10,
) -> pd.DataFrame:
    if metric not in METRIC_LABELS:
        raise ValueError(f"Métrica no soportada: {metric}")
    return dataframe.nlargest(limit, metric).copy()


def build_type_distribution(dataframe: pd.DataFrame) -> pd.DataFrame:
    if dataframe.empty:
        return pd.DataFrame(columns=["type", "pokemon_count"])

    exploded = (
        dataframe.assign(type=dataframe["types"].str.split(", "))
        .explode("type")
        .dropna(subset=["type"])
    )
    return (
        exploded.groupby("type", as_index=False)
        .agg(pokemon_count=("id", "nunique"))
        .sort_values("pokemon_count", ascending=False)
    )
