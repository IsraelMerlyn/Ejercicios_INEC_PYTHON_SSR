from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping

from utils.date_utils import parse_iso_datetime


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


@dataclass(frozen=True, slots=True)
class PriceRecord:
    """Snapshot temporal de datos de mercado para un activo."""

    asset_id: str
    current_price: float
    market_cap: float | None
    total_volume: float | None
    price_change_percentage_24h: float | None
    high_24h: float | None
    low_24h: float | None
    recorded_at: datetime
    currency: str

    @classmethod
    def from_api(
        cls,
        payload: Mapping[str, Any],
        currency: str,
    ) -> "PriceRecord":
        asset_id = str(payload.get("id") or "").strip()
        if not asset_id:
            raise ValueError("El registro de precio no contiene asset_id.")

        current_price_raw = payload.get("current_price")
        if current_price_raw is None:
            raise ValueError(f"{asset_id}: current_price es nulo.")

        current_price = float(current_price_raw)
        if current_price <= 0:
            raise ValueError(f"{asset_id}: current_price debe ser positivo.")

        last_updated = payload.get("last_updated")
        if not last_updated:
            raise ValueError(f"{asset_id}: last_updated es obligatorio.")

        normalized_currency = currency.strip().lower()
        if not normalized_currency:
            raise ValueError("La moneda no puede estar vacía.")

        return cls(
            asset_id=asset_id,
            current_price=current_price,
            market_cap=_optional_float(payload.get("market_cap")),
            total_volume=_optional_float(payload.get("total_volume")),
            price_change_percentage_24h=_optional_float(
                payload.get("price_change_percentage_24h")
            ),
            high_24h=_optional_float(payload.get("high_24h")),
            low_24h=_optional_float(payload.get("low_24h")),
            recorded_at=parse_iso_datetime(str(last_updated)),
            currency=normalized_currency,
        )
