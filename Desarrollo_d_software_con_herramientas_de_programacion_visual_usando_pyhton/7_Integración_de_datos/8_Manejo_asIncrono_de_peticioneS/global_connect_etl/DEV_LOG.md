# Dev Log

## Incidencias y correcciones

### 1. Riesgo: insertar registro por registro

**Problema:** El ejercicio penaliza el enfoque de insertar uno por uno cuando el volumen supera los 100 elementos.

**Corrección:** La capa `DatabaseManager` usa `executemany()` en todas las tablas para realizar inserciones masivas.

### 2. Riesgo: acoplar el código al JSON crudo

**Problema:** Si el JSON cambia, una solución acoplada obligaría a modificar muchas partes del código.

**Corrección:** Se agregaron dataclasses intermedias en `models.py` y transformadores específicos en `transformers.py`.

### 3. Riesgo: errores de datos rompiendo toda la ejecución

**Problema:** Un registro incompleto puede detener el ETL.

**Corrección:** Cada transformador registra errores recuperables en `TransformResult.errors` y luego los persiste en `etl_errors`.

### 4. Riesgo: credenciales expuestas

**Problema:** Las credenciales no deben estar hardcodeadas ni imprimirse en logs.

**Corrección:** Se usan variables de entorno y `.env.example`. El cliente HTTP enmascara valores sensibles en cuerpos de error cuando aparecen.
