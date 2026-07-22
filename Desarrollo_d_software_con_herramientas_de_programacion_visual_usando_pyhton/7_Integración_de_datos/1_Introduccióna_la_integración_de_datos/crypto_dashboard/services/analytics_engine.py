from __future__ import annotations

from typing import Any

import pandas as pd


def latest_per_asset(history: pd.DataFrame) -> pd.DataFrame:
    if history.empty:
        return history.copy()

    ordered = history.sort_values("recorded_at")
    return ordered.groupby("asset_id", as_index=False).tail(1).copy()


def add_moving_average(
    history: pd.DataFrame,
    window: int = 7,
) -> pd.DataFrame:
    if history.empty:
        result = history.copy()
        result["moving_average"] = pd.Series(dtype="float64")
        return result

    result = history.sort_values(["asset_id", "recorded_at"]).copy()
    result["moving_average"] = (
        result.groupby("asset_id")["current_price"]
        .transform(lambda series: series.rolling(window, min_periods=1).mean())
    )
    return result


def calculate_volatility(history: pd.DataFrame, asset_id: str) -> float:
    asset_history = (
        history.loc[history["asset_id"] == asset_id]
        .sort_values("recorded_at")["current_price"]
        .dropna()
    )
    if len(asset_history) < 2:
        return 0.0

    returns = asset_history.pct_change().dropna()
    if returns.empty:
        return 0.0
    return float(returns.std(ddof=0) * 100)


def calculate_asset_kpis(
    history: pd.DataFrame,
    asset_id: str,
) -> dict[str, Any]:
    asset_history = history.loc[history["asset_id"] == asset_id].sort_values(
        "recorded_at"
    )
    if asset_history.empty:
        raise ValueError(f"No hay datos para el activo {asset_id!r}.")

    latest = asset_history.iloc[-1]
    return {
        "asset_id": asset_id,
        "name": latest["name"],
        "symbol": latest["symbol"],
        "current_price": float(latest["current_price"]),
        "change_24h": float(latest["price_change_percentage_24h"] or 0.0),
        "market_cap": float(latest["market_cap"] or 0.0),
        "total_volume": float(latest["total_volume"] or 0.0),
        "high_24h": float(latest["high_24h"] or 0.0),
        "low_24h": float(latest["low_24h"] or 0.0),
        "volatility": calculate_volatility(history, asset_id),
        "recorded_at": latest["recorded_at"],
    }


def top_gainers(history: pd.DataFrame, limit: int = 5) -> pd.DataFrame:
    latest = latest_per_asset(history)
    if latest.empty:
        return latest
    return latest.sort_values(
        "price_change_percentage_24h",
        ascending=False,
        na_position="last",
    ).head(limit)


def format_money(value: float, currency: str) -> str:
    currency_symbol = {
        "usd": "US$",
        "mxn": "MX$",
        "eur": "€",
    }.get(currency.lower(), f"{currency.upper()} ")

    absolute = abs(value)
    if absolute >= 1_000_000_000_000:
        return f"{currency_symbol}{value / 1_000_000_000_000:,.2f} Bn"
    if absolute >= 1_000_000_000:
        return f"{currency_symbol}{value / 1_000_000_000:,.2f} mil M"
    if absolute >= 1_000_000:
        return f"{currency_symbol}{value / 1_000_000:,.2f} M"
    if absolute >= 1:
        return f"{currency_symbol}{value:,.2f}"
    return f"{currency_symbol}{value:,.6f}"
