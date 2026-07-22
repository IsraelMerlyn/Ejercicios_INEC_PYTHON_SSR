# Diagrama ERD - Global-Connect ETL

```mermaid
erDiagram
    users ||--|| addresses : tiene
    users ||--o{ subscriptions : contrata
    financial_assets ||--o{ asset_price_history : registra
    weather_locations ||--o{ weather_observations : observa
    weather_locations ||--o{ weather_forecasts : pronostica

    users {
        TEXT external_id PK
        TEXT full_name
        TEXT email UK
        TEXT status
        TEXT created_at_utc
    }

    addresses {
        INTEGER id PK
        TEXT user_external_id FK
        TEXT city
        TEXT country
        REAL latitude
        REAL longitude
    }

    subscriptions {
        INTEGER id PK
        TEXT user_external_id FK
        TEXT plan_name
        NUMERIC price_usd
        INTEGER active
        TEXT started_at_utc
    }

    financial_assets {
        TEXT external_id PK
        TEXT symbol UK
        TEXT name
        TEXT sector
        TEXT currency
        TEXT listed_at_utc
    }

    asset_price_history {
        INTEGER id PK
        TEXT asset_external_id FK
        NUMERIC price_usd
        NUMERIC volume
        TEXT recorded_at_utc
    }

    weather_locations {
        TEXT external_id PK
        TEXT city
        TEXT country
        REAL latitude
        REAL longitude
    }

    weather_observations {
        INTEGER id PK
        TEXT location_external_id FK
        REAL temperature_c
        INTEGER humidity
        TEXT condition
        TEXT observed_at_utc
    }

    weather_forecasts {
        INTEGER id PK
        TEXT location_external_id FK
        TEXT forecast_date
        REAL min_temp_c
        REAL max_temp_c
        REAL rain_probability
    }
```

## Decisión de modelado

El JSON externo se recibe con campos anidados y listas internas. La base no guarda el JSON crudo como una sola columna porque eso dificultaría consultas analíticas. En su lugar, se normaliza en tablas relacionales con claves primarias, claves foráneas y restricciones de unicidad.

Ejemplo de anidación mapeada:

```text
data -> attributes -> history -> values[]
```

Se convierte en:

```text
financial_assets 1 ─── N asset_price_history
```
