# Informe Técnico de Arquitectura

## Proyecto

**Operación Puente de Datos: El Arquitecto de la Integración en Tiempo Real**

El objetivo del proyecto es demostrar una arquitectura de integración resiliente en Python usando `requests`, clientes HTTP reutilizables, modelos intermedios, validación, logging, caché, retries con backoff exponencial y persistencia local en SQLite.

## Diagnóstico inicial de endpoints críticos

| Servicio | Endpoint demo | Método | Autenticación simulada | Rate limit asumido | Candidato a caché |
|---|---:|---:|---|---:|---|
| Identidad de conductores | `/identity/verify` | POST | `X-Identity-Key` desde `.env` | 60/min | Sí, 15 min |
| Rastreo de flota | `/fleet/vehicles/{id}/location` | GET | Bearer token desde `.env` | 60/min | Sí, máximo 3 seg |
| Clima por ubicación | `/weather/current` | GET | `X-API-Key` desde `.env` | 60/min | Sí, 10 min |

La autenticación no está hardcodeada. Las credenciales se leen desde `.env` y los logs nunca imprimen valores sensibles.

## Esquemas JSON esperados

### Identidad

```json
{
  "driverId": "D-1001",
  "profile": {
    "fullName": "ana martinez"
  },
  "compliance": {
    "licenseStatus": "ACTIVE",
    "verified": true,
    "riskScore": 0.08
  },
  "updatedAt": "2026-07-21T18:30:00Z"
}
```

### Rastreo

```json
{
  "vehicleId": "V-1001",
  "driverId": "D-1001",
  "location": {
    "coordinates": {
      "lat": "19.4326",
      "lon": "-99.1332"
    }
  },
  "speedKmh": "42.5",
  "status": "IN_TRANSIT",
  "capturedAt": "2026-07-21T18:30:00Z"
}
```

### Clima

```json
{
  "location": {
    "city": "Ciudad de Mexico",
    "lat": "19.4326",
    "lon": "-99.1332"
  },
  "measurements": {
    "temp_celsius": 22.4,
    "condition": "clear"
  },
  "observedAt": "2026-07-21T18:30:00Z"
}
```

## Decisiones de diseño

### Clase base `APIClient`

Se creó una clase base para evitar tres scripts desconectados. Esta clase concentra:

- `requests.Session` para reutilizar conexiones TCP.
- Timeouts de conexión y lectura.
- Headers comunes.
- Reintentos con backoff exponencial y jitter.
- Manejo de códigos transitorios: `429`, `500`, `502`, `503`, `504`.
- No reintentar errores permanentes `400`, `401`, `403`, `404`.
- Caché en memoria con TTL.
- Logging estructurado.
- Redacción de secretos en errores y logs.

Este enfoque funciona como una mezcla de **Adapter** y **Facade**. Cada servicio específico adapta el contrato externo a un modelo interno estable.

### Modelos intermedios

Los modelos `DriverIdentity`, `FleetPosition` y `WeatherSnapshot` desacoplan el JSON externo de la aplicación interna.

Si la API de clima cambia `temp_celsius` por `temperature_c`, solo habría que modificar `WeatherSnapshot.from_provider()`. El resto del sistema no se enteraría del cambio.

### Persistencia

SQLite se usa para registrar los resultados transformados. La base incluye:

- `drivers`
- `vehicle_positions`
- `weather_snapshots`
- `sync_runs`

Se usan consultas parametrizadas y transacciones para evitar inyección SQL y mantener integridad.

## Manejo de fallos

La capa superior (`main.py`) usa degradación elegante:

- Si falla identidad, registra el error y continúa.
- Si falla ubicación de un vehículo, omite el clima de ese vehículo.
- Si falla clima, conserva la posición y continúa con el siguiente vehículo.

Esto evita que una API caída congele toda la operación.

## Complejidad temporal y espacial

Sea `D` el número de conductores y `V` el número de vehículos:

- Tiempo normal: `O(D + V)` llamadas principales más `O(V)` llamadas de clima.
- Espacio en memoria: `O(C)` por caché, donde `C` es la cantidad de respuestas vigentes por TTL.
- Persistencia: crece proporcionalmente al número de sincronizaciones y vehículos procesados.

El uso de `requests.Session` reduce overhead de conexión frente a una implementación naive que abre una conexión nueva por cada petición.

## Catálogo de errores personalizados

| Excepción | Significado | Manejo recomendado |
|---|---|---|
| `IntegrationError` | Error base de integración | Captura general en orquestador |
| `APIConnectionError` | Timeout o conexión fallida | Reintentar y degradar |
| `APIRateLimitExceeded` | HTTP 429 persistente | Aumentar TTL o reducir frecuencia |
| `APIServerError` | HTTP 5xx persistente | Reintentar con backoff |
| `APIClientError` | HTTP 4xx permanente | Corregir request/configuración |
| `APIAuthenticationError` | HTTP 401/403 | Revisar credenciales |
| `InvalidResponseFormat` | JSON inválido o contrato roto | Revisar proveedor/adaptador |
| `DataValidationError` | Datos corruptos o faltantes | Evitar persistir información inválida |

## Seguridad

Las claves API no se imprimen. La prueba `test_credentials_are_not_exposed_in_error_logs` valida que los secretos no aparezcan en logs incluso si el proveedor devuelve un error crítico.

## Modo caos

Con `CHAOS_MODE=true`, el proveedor demo genera retardos, errores `500` y errores `429`. Esto permite observar si los logs explican claramente el fallo y si los retries se comportan correctamente.
