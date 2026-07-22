from __future__ import annotations

from datetime import datetime, timezone


def parse_iso_datetime(value: str) -> datetime:
    """Convierte una fecha ISO 8601 a datetime UTC consciente de zona horaria."""

    if not isinstance(value, str) or not value.strip():
        raise ValueError("La fecha ISO 8601 no puede estar vacía.")

    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"Fecha ISO 8601 inválida: {value!r}") from exc

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)


def to_sql_datetime(value: datetime) -> str:
    """Serializa datetime en un formato UTC comparable dentro de SQLite."""

    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds")
