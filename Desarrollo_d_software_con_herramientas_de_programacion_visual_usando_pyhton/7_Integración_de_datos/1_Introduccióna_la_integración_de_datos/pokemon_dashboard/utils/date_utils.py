from __future__ import annotations

from datetime import datetime, timezone


def parse_iso_datetime(value: str) -> datetime:
    """Convierte una fecha ISO 8601 a datetime UTC con zona horaria."""

    normalized = value.strip()
    if not normalized:
        raise ValueError("La fecha ISO 8601 no puede estar vacía.")

    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"Fecha ISO 8601 inválida: {value!r}") from exc

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)


def utc_now_iso() -> str:
    """Retorna la hora actual UTC en formato ISO 8601 estable para SQLite."""

    return datetime.now(timezone.utc).isoformat(timespec="seconds")
