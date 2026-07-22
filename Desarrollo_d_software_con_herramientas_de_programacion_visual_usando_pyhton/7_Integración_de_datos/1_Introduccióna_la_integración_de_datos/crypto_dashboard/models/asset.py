from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class Asset:
    """Entidad de catálogo para una criptomoneda."""

    id: str
    symbol: str
    name: str
    image_url: str | None
    market_cap_rank: int | None

    @classmethod
    def from_api(cls, payload: Mapping[str, Any]) -> "Asset":
        asset_id = str(payload.get("id") or "").strip()
        symbol = str(payload.get("symbol") or "").strip().upper()
        name = str(payload.get("name") or "").strip()

        if not asset_id:
            raise ValueError("El activo no contiene un id válido.")
        if not symbol:
            raise ValueError(f"El activo {asset_id!r} no contiene symbol.")
        if not name:
            raise ValueError(f"El activo {asset_id!r} no contiene name.")

        rank = payload.get("market_cap_rank")
        market_cap_rank = int(rank) if rank is not None else None

        image = payload.get("image")
        image_url = str(image).strip() if image else None

        return cls(
            id=asset_id,
            symbol=symbol,
            name=name,
            image_url=image_url,
            market_cap_rank=market_cap_rank,
        )
