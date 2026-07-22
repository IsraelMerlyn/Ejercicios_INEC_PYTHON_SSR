from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from config.settings import STAT_NAMES
from utils.exceptions import DataValidationError


def _generation_from_id(pokemon_id: int) -> int:
    limits = (151, 251, 386, 493, 649, 721, 809, 905)
    for generation, upper_limit in enumerate(limits, start=1):
        if pokemon_id <= upper_limit:
            return generation
    return 9


@dataclass(frozen=True, slots=True)
class Pokemon:
    """Modelo de dominio desacoplado de la respuesta cruda de PokéAPI."""

    id: int
    name: str
    base_experience: int | None
    height_dm: int
    weight_hg: int
    image_url: str | None
    generation: int
    abilities: tuple[str, ...]
    types: tuple[tuple[int, str], ...]
    stats: dict[str, int]

    @property
    def height_m(self) -> float:
        return self.height_dm / 10

    @property
    def weight_kg(self) -> float:
        return self.weight_hg / 10

    @classmethod
    def from_api(cls, payload: Mapping[str, Any]) -> "Pokemon":
        try:
            pokemon_id = int(payload["id"])
            raw_name = str(payload["name"]).strip()
            height_dm = int(payload["height"])
            weight_hg = int(payload["weight"])
        except (KeyError, TypeError, ValueError) as exc:
            raise DataValidationError(
                "El Pokémon no contiene id, name, height y weight válidos."
            ) from exc

        if pokemon_id <= 0:
            raise DataValidationError("El id del Pokémon debe ser positivo.")
        if not raw_name:
            raise DataValidationError("El nombre del Pokémon es obligatorio.")
        if height_dm <= 0 or weight_hg <= 0:
            raise DataValidationError("Altura y peso deben ser positivos.")

        raw_experience = payload.get("base_experience")
        base_experience = (
            int(raw_experience) if raw_experience is not None else None
        )
        if base_experience is not None and base_experience < 0:
            raise DataValidationError("La experiencia base no puede ser negativa.")

        parsed_types: list[tuple[int, str]] = []
        for item in payload.get("types") or []:
            try:
                slot = int(item["slot"])
                type_name = str(item["type"]["name"]).strip().lower()
            except (KeyError, TypeError, ValueError) as exc:
                raise DataValidationError("La estructura de types es inválida.") from exc
            if type_name:
                parsed_types.append((slot, type_name))

        if not parsed_types:
            raise DataValidationError(f"{raw_name}: debe contener al menos un tipo.")

        parsed_stats: dict[str, int] = {}
        for item in payload.get("stats") or []:
            try:
                stat_name = str(item["stat"]["name"]).strip().lower()
                base_stat = int(item["base_stat"])
            except (KeyError, TypeError, ValueError) as exc:
                raise DataValidationError("La estructura de stats es inválida.") from exc
            if stat_name in STAT_NAMES:
                parsed_stats[stat_name] = base_stat

        missing_stats = set(STAT_NAMES) - set(parsed_stats)
        if missing_stats:
            missing = ", ".join(sorted(missing_stats))
            raise DataValidationError(f"{raw_name}: faltan estadísticas: {missing}.")

        abilities: list[str] = []
        for item in payload.get("abilities") or []:
            ability = item.get("ability") if isinstance(item, Mapping) else None
            if isinstance(ability, Mapping):
                name = str(ability.get("name") or "").strip().lower()
                if name:
                    abilities.append(name)

        sprites = payload.get("sprites") or {}
        official_artwork = (
            sprites.get("other", {})
            .get("official-artwork", {})
            .get("front_default")
            if isinstance(sprites, Mapping)
            else None
        )
        fallback_sprite = (
            sprites.get("front_default") if isinstance(sprites, Mapping) else None
        )
        image_url = official_artwork or fallback_sprite

        return cls(
            id=pokemon_id,
            name=raw_name.replace("-", " ").title(),
            base_experience=base_experience,
            height_dm=height_dm,
            weight_hg=weight_hg,
            image_url=str(image_url) if image_url else None,
            generation=_generation_from_id(pokemon_id),
            abilities=tuple(dict.fromkeys(abilities)),
            types=tuple(sorted(parsed_types, key=lambda value: value[0])),
            stats=parsed_stats,
        )
