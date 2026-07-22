"""Transformadores ETL para convertir JSON anidado a modelos internos."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Iterable

from exceptions import DataValidationError, InvalidResponseFormat
from models import (
    AddressRecord,
    AssetPriceRecord,
    AssetRecord,
    SubscriptionRecord,
    UserRecord,
    WeatherForecastRecord,
    WeatherLocationRecord,
    WeatherObservationRecord,
    parse_datetime,
    parse_decimal,
    parse_float,
)

logger = logging.getLogger("global_connect.transformers")


@dataclass
class TransformResult:
    """Resultado de transformación con datos válidos y errores recuperables."""

    records: dict[str, list[Any]] = field(default_factory=dict)
    errors: list[dict[str, str]] = field(default_factory=list)

    def add_error(self, source: str, external_id: str, error: Exception, payload: Any) -> None:
        """Registra errores de mapeo sin detener todo el proceso ETL."""
        self.errors.append(
            {
                "source": source,
                "external_id": external_id or "UNKNOWN",
                "error_type": error.__class__.__name__,
                "message": str(error),
                "raw_payload": json.dumps(payload, ensure_ascii=False, default=str)[:2000],
            }
        )


def require_dict(payload: Any, source: str) -> dict[str, Any]:
    """Valida que la respuesta raíz sea un diccionario."""
    if not isinstance(payload, dict):
        raise InvalidResponseFormat(f"La respuesta de {source} no es un objeto JSON")
    return payload


def require_list(payload: dict[str, Any], key: str, source: str) -> list[dict[str, Any]]:
    """Valida que una llave del JSON contenga una lista de diccionarios."""
    value = payload.get(key)
    if not isinstance(value, list):
        raise InvalidResponseFormat(f"La llave {key} de {source} no contiene una lista")
    return value


def transform_users(payload: dict[str, Any]) -> TransformResult:
    """Transforma JSON de usuarios, direcciones y suscripciones."""
    response = require_dict(payload, "users")
    rows = require_list(response, "data", "users")
    result = TransformResult(records={"users": [], "addresses": [], "subscriptions": []})

    for row in rows:
        external_id = str(row.get("id") or "")
        try:
            profile = row["profile"]
            name = profile["name"]
            address = profile["address"]
            geo = address["geo"]

            # Aquí se desanida profile -> name y se unifica en un nombre completo estable.
            full_name = f"{name.get('first', '').strip()} {name.get('last', '').strip()}".strip()
            if not external_id or not full_name or not profile.get("email"):
                raise DataValidationError("Faltan campos críticos del usuario")

            user = UserRecord(
                external_id=external_id,
                full_name=full_name.title(),
                email=str(profile["email"]).strip().lower(),
                status=str(profile.get("status") or "unknown").lower(),
                created_at_utc=parse_datetime(profile.get("created_at"), "profile.created_at"),
            )
            user_address = AddressRecord(
                user_external_id=external_id,
                city=str(address.get("city") or "Sin ciudad").title(),
                country=str(address.get("country") or "NA").upper(),
                latitude=parse_float(geo.get("lat"), "address.geo.lat"),
                longitude=parse_float(geo.get("lng"), "address.geo.lng"),
            )

            result.records["users"].append(user)
            result.records["addresses"].append(user_address)

            for subscription in row.get("subscriptions", []):
                result.records["subscriptions"].append(
                    SubscriptionRecord(
                        user_external_id=external_id,
                        plan_name=str(subscription.get("plan") or "free").lower(),
                        price_usd=parse_decimal(subscription.get("price_usd"), "subscription.price_usd"),
                        active=bool(subscription.get("active")),
                        started_at_utc=parse_datetime(
                            subscription.get("started_at"), "subscription.started_at"
                        ),
                    )
                )
        except (KeyError, TypeError, DataValidationError) as exc:
            logger.warning("user_mapping_error external_id=%s error=%s", external_id, exc)
            result.add_error("users", external_id, exc, row)

    return result


def transform_assets(payload: dict[str, Any]) -> TransformResult:
    """Transforma JSON financiero con historial anidado en tablas normalizadas."""
    response = require_dict(payload, "assets")
    rows = require_list(response, "data", "assets")
    result = TransformResult(records={"assets": [], "asset_prices": []})

    for row in rows:
        external_id = str(row.get("id") or "")
        try:
            attributes = row["attributes"]
            market = attributes["market"]
            history = attributes["history"]
            values = history["values"]

            if not external_id or not attributes.get("symbol") or not attributes.get("name"):
                raise DataValidationError("Faltan campos críticos del activo financiero")
            if not isinstance(values, list):
                raise DataValidationError("history.values debe ser una lista")

            asset = AssetRecord(
                external_id=external_id,
                symbol=str(attributes["symbol"]).upper(),
                name=str(attributes["name"]).strip().title(),
                sector=str(market.get("sector") or "unknown").lower(),
                currency=str(market.get("currency") or "USD").upper(),
                listed_at_utc=parse_datetime(attributes.get("listed_at"), "attributes.listed_at"),
            )
            result.records["assets"].append(asset)

            for item in values:
                # Este es el mapeo profundo solicitado: data -> attributes -> history -> values[].
                result.records["asset_prices"].append(
                    AssetPriceRecord(
                        asset_external_id=external_id,
                        price_usd=parse_decimal(item.get("price_usd"), "history.values.price_usd"),
                        volume=parse_decimal(item.get("volume"), "history.values.volume"),
                        recorded_at_utc=parse_datetime(item.get("timestamp"), "history.values.timestamp"),
                    )
                )
        except (KeyError, TypeError, DataValidationError) as exc:
            logger.warning("asset_mapping_error external_id=%s error=%s", external_id, exc)
            result.add_error("assets", external_id, exc, row)

    return result


def transform_weather(payload: dict[str, Any]) -> TransformResult:
    """Transforma JSON meteorológico de ciudades, observaciones y pronósticos."""
    response = require_dict(payload, "weather")
    rows = require_list(response, "data", "weather")
    result = TransformResult(
        records={"weather_locations": [], "weather_observations": [], "weather_forecasts": []}
    )

    for row in rows:
        external_id = str(row.get("id") or "")
        try:
            location = row["location"]
            coordinates = location["coordinates"]
            current = row["current"]
            forecast = row.get("forecast", [])

            if not external_id or not location.get("city"):
                raise DataValidationError("Faltan campos críticos de ubicación climática")

            result.records["weather_locations"].append(
                WeatherLocationRecord(
                    external_id=external_id,
                    city=str(location["city"]).title(),
                    country=str(location.get("country") or "NA").upper(),
                    latitude=parse_float(coordinates.get("lat"), "location.coordinates.lat"),
                    longitude=parse_float(coordinates.get("lon"), "location.coordinates.lon"),
                )
            )

            result.records["weather_observations"].append(
                WeatherObservationRecord(
                    location_external_id=external_id,
                    temperature_c=parse_float(current.get("temp_celsius"), "current.temp_celsius"),
                    humidity=int(parse_float(current.get("humidity"), "current.humidity")),
                    condition=str(current.get("condition") or "unknown").lower(),
                    observed_at_utc=parse_datetime(current.get("observed_at"), "current.observed_at"),
                )
            )

            for day in forecast:
                result.records["weather_forecasts"].append(
                    WeatherForecastRecord(
                        location_external_id=external_id,
                        forecast_date=str(day.get("date") or ""),
                        min_temp_c=parse_float(day.get("min_temp_c"), "forecast.min_temp_c"),
                        max_temp_c=parse_float(day.get("max_temp_c"), "forecast.max_temp_c"),
                        rain_probability=parse_float(day.get("rain_probability"), "forecast.rain_probability"),
                    )
                )
        except (KeyError, TypeError, DataValidationError) as exc:
            logger.warning("weather_mapping_error external_id=%s error=%s", external_id, exc)
            result.add_error("weather", external_id, exc, row)

    return result


def merge_results(results: Iterable[TransformResult]) -> TransformResult:
    """Une resultados de diferentes transformadores para cargar en bloque."""
    merged = TransformResult(records={}, errors=[])
    for result in results:
        for table_name, records in result.records.items():
            merged.records.setdefault(table_name, []).extend(records)
        merged.errors.extend(result.errors)
    return merged
