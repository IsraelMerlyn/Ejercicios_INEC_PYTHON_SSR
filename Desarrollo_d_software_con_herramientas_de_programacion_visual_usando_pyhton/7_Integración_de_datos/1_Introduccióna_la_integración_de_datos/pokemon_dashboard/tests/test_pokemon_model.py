import pytest

from models.pokemon import Pokemon
from utils.exceptions import DataValidationError


def _payload() -> dict[str, object]:
    return {
        "id": 25,
        "name": "pikachu",
        "base_experience": 112,
        "height": 4,
        "weight": 60,
        "abilities": [{"ability": {"name": "static"}}],
        "types": [{"slot": 1, "type": {"name": "electric"}}],
        "stats": [
            {"base_stat": 35, "stat": {"name": "hp"}},
            {"base_stat": 55, "stat": {"name": "attack"}},
            {"base_stat": 40, "stat": {"name": "defense"}},
            {"base_stat": 50, "stat": {"name": "special-attack"}},
            {"base_stat": 50, "stat": {"name": "special-defense"}},
            {"base_stat": 90, "stat": {"name": "speed"}},
        ],
        "sprites": {"front_default": "https://example.com/pikachu.png"},
    }


def test_pokemon_model_transforms_api_payload() -> None:
    pokemon = Pokemon.from_api(_payload())

    assert pokemon.id == 25
    assert pokemon.name == "Pikachu"
    assert pokemon.height_m == 0.4
    assert pokemon.weight_kg == 6.0
    assert pokemon.types == ((1, "electric"),)
    assert pokemon.stats["speed"] == 90


def test_pokemon_model_rejects_missing_stats() -> None:
    payload = _payload()
    payload["stats"] = []

    with pytest.raises(DataValidationError, match="faltan estadísticas"):
        Pokemon.from_api(payload)
