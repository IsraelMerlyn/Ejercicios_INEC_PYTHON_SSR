"""Excepciones personalizadas para la capa de integración."""


class IntegrationError(Exception):
    """Excepción base para errores controlados del ETL."""


class APIConnectionError(IntegrationError):
    """Se lanza cuando no fue posible comunicarse con la API externa."""


class APIRateLimitExceeded(IntegrationError):
    """Se lanza cuando el proveedor responde con límite de peticiones."""


class APIResponseError(IntegrationError):
    """Se lanza cuando la API responde con un estado HTTP no exitoso."""


class InvalidResponseFormat(IntegrationError):
    """Se lanza cuando la respuesta no tiene JSON válido o estructura esperada."""


class DataValidationError(IntegrationError):
    """Se lanza cuando un registro no cumple el contrato de datos interno."""
