# Informe Técnico de Arquitectura

## Proyecto

**The Data Architect Challenge: Construyendo el Nexo de Información**  
**Solución:** Global-Connect ETL  
**Autor:** Josué Israel Vásquez Martínez

## 1. Diagnóstico inicial

Global-Connect necesita integrar tres proveedores externos para construir un panel de analíticas:

1. Proveedor de usuarios.
2. Proveedor financiero.
3. Proveedor meteorológico.

El problema principal no es solo consumir APIs con `GET`, sino convertir respuestas JSON heterogéneas en información confiable para una base relacional.

## 2. Endpoints simulados

| Proveedor | Endpoint | Método | Autenticación simulada | Rate limit esperado |
|---|---|---:|---|---:|
| Usuarios | `/api/v1/users` | GET | Bearer Token + API Key | 60 req/min |
| Finanzas | `/api/v1/finance/assets` | GET | Bearer Token + API Key | 30 req/min |
| Clima | `/api/v1/weather/cities` | GET | Bearer Token + API Key | 60 req/min |

Las credenciales se cargan desde `.env`, no se escriben directamente en el código.

## 3. Diseño arquitectónico

La solución se divide en capas:

```text
main.py
  ↓
services/*_service.py
  ↓
APIClient
  ↓
Demo API REST local
  ↓
transformers.py
  ↓
models.py
  ↓
database.py
  ↓
SQLite
```

## 4. Patrón ETL

### Extract

`APIClient` usa:

- `requests.Session` para reutilizar conexiones.
- Headers comunes.
- Bearer Token y API Key simuladas.
- Timeout configurable.
- Reintentos ante 429, 500, 502, 503 y 504.
- Backoff exponencial.
- Jitter.
- Caché con TTL para GET.

### Transform

Los transformadores convierten JSON anidado a dataclasses internas:

- `UserRecord`
- `AddressRecord`
- `SubscriptionRecord`
- `AssetRecord`
- `AssetPriceRecord`
- `WeatherLocationRecord`
- `WeatherObservationRecord`
- `WeatherForecastRecord`

La transformación más compleja es:

```text
data -> attributes -> history -> values[]
```

Se convierte en:

```text
financial_assets
asset_price_history
```

### Load

`DatabaseManager` usa SQLite y `executemany()` para inserciones masivas. Esto evita insertar fila por fila cuando el volumen rebasa 100 registros.

## 5. Manejo de errores

El proyecto usa una jerarquía propia:

| Excepción | Uso |
|---|---|
| `IntegrationError` | Clase base |
| `APIConnectionError` | Fallo de red o timeout final |
| `APIRateLimitExceeded` | Rate limit persistente |
| `APIResponseError` | Error HTTP permanente |
| `InvalidResponseFormat` | JSON inválido o estructura inesperada |
| `DataValidationError` | Registro inválido durante transformación |

Los registros corruptos se guardan en `etl_errors` en lugar de romper la ejecución completa.

## 6. Seguridad

- No hay credenciales hardcodeadas.
- `.env.example` documenta las variables necesarias.
- `.env` está ignorado en `.gitignore`.
- `APIClient` enmascara secretos si aparecen accidentalmente en cuerpos de error.

## 7. Complejidad temporal y espacial

Sea `n` el número de registros por endpoint.

### Tiempo

- Extracción: `O(1)` por endpoint desde la perspectiva del cliente, aunque depende del proveedor.
- Transformación usuarios: `O(n)`.
- Transformación activos: `O(n * h)`, donde `h` es la cantidad de puntos históricos por activo.
- Transformación clima: `O(n * f)`, donde `f` es la cantidad de días de pronóstico.
- Carga en SQLite: `O(n)` usando bulk inserts.

Con `limit=50`, el sistema procesa 700 registros normalizados en menos de 2 segundos en entorno local.

### Espacio

El proyecto mantiene los registros transformados en memoria antes de insertar. Por tanto, el espacio es `O(n + n*h + n*f)`. Para volúmenes empresariales grandes, la mejora natural sería procesar por páginas o chunks.

## 8. Pruebas de estrés

### JSON vacío

Comando:

```bash
python main.py --reset-db --empty
```

Resultado esperado: el sistema no falla y genera una corrida con cero registros de negocio.

### Fallos aleatorios

Comando:

```bash
python main.py --reset-db --chaos
```

Resultado esperado: el cliente reintenta errores transitorios y registra los fallos persistentes.

### Pruebas unitarias

Comando:

```bash
pytest -q
```

Las pruebas validan:

- Retry ante 500.
- No retry ante 404.
- JSON inválido.
- Caché.
- Conversión de fechas.
- Conversión de decimales.
- Mapeo profundo.
- Bulk insert con más de 100 registros.

## 9. Decisión crítica: modelo intermedio

Si el proveedor meteorológico cambia `temp_celsius` por `temperature_c`, solo se modifica `transform_weather()`. La base de datos, el resto del ETL y los reportes no cambian.

Esta decisión desacopla el contrato externo del contrato interno y mejora la mantenibilidad a largo plazo.
