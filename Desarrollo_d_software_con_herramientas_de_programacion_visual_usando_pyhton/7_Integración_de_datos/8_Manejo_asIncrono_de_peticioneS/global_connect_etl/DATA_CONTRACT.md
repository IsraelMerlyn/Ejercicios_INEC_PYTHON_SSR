# Contrato de Datos - Global-Connect ETL

Este documento describe cómo se mapean los campos de las APIs externas al modelo interno estable.

## Proveedor de usuarios

| JSON externo | Tipo recibido | Tabla destino | Columna destino | Tipo destino | Regla |
|---|---:|---|---|---|---|
| `id` | string | `users` | `external_id` | TEXT PK | Obligatorio |
| `profile.name.first` + `profile.name.last` | string | `users` | `full_name` | TEXT | Se concatena y se aplica Title Case |
| `profile.email` | string | `users` | `email` | TEXT UNIQUE | Lowercase y trim |
| `profile.status` | string/null | `users` | `status` | TEXT | Default `unknown` |
| `profile.created_at` | ISO 8601 | `users` | `created_at_utc` | TEXT | Convertido a UTC |
| `profile.address.geo.lat` | string | `addresses` | `latitude` | REAL | Convertido a float |
| `profile.address.geo.lng` | string | `addresses` | `longitude` | REAL | Convertido a float |
| `subscriptions[].price_usd` | string | `subscriptions` | `price_usd` | NUMERIC | Convertido a Decimal/float |

## Proveedor financiero

| JSON externo | Tipo recibido | Tabla destino | Columna destino | Tipo destino | Regla |
|---|---:|---|---|---|---|
| `id` | string | `financial_assets` | `external_id` | TEXT PK | Obligatorio |
| `attributes.symbol` | string | `financial_assets` | `symbol` | TEXT UNIQUE | Uppercase |
| `attributes.name` | string | `financial_assets` | `name` | TEXT | Title Case |
| `attributes.market.sector` | string/null | `financial_assets` | `sector` | TEXT | Lowercase/default `unknown` |
| `attributes.market.currency` | string | `financial_assets` | `currency` | TEXT | Uppercase |
| `attributes.history.values[].price_usd` | string | `asset_price_history` | `price_usd` | NUMERIC | Convertido a Decimal/float |
| `attributes.history.values[].volume` | string | `asset_price_history` | `volume` | NUMERIC | Convertido a Decimal/float |
| `attributes.history.values[].timestamp` | ISO 8601 | `asset_price_history` | `recorded_at_utc` | TEXT | Convertido a UTC |

## Proveedor meteorológico

| JSON externo | Tipo recibido | Tabla destino | Columna destino | Tipo destino | Regla |
|---|---:|---|---|---|---|
| `id` | string | `weather_locations` | `external_id` | TEXT PK | Obligatorio |
| `location.city` | string | `weather_locations` | `city` | TEXT | Title Case |
| `location.coordinates.lat` | string | `weather_locations` | `latitude` | REAL | Convertido a float |
| `current.temp_celsius` | string | `weather_observations` | `temperature_c` | REAL | Convertido a float |
| `current.humidity` | string | `weather_observations` | `humidity` | INTEGER | Convertido a entero |
| `forecast[].rain_probability` | string | `weather_forecasts` | `rain_probability` | REAL | Convertido a float |

## Manejo de errores

Si falta un campo obligatorio, el registro no rompe la ejecución. Se almacena en `etl_errors` con:

- fuente del error,
- identificador externo,
- tipo de error,
- mensaje,
- payload original recortado.

Esto permite auditar la calidad de datos sin perder toda la corrida del ETL.
