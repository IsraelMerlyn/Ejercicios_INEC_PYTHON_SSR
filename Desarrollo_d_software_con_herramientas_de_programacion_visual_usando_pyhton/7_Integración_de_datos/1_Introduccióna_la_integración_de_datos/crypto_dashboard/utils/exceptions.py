class DataSourceError(RuntimeError):
    """Error base relacionado con fuentes externas de datos."""


class DataSourceConnectionError(DataSourceError):
    """No fue posible establecer conexión con la API."""


class DataSourceTimeoutError(DataSourceError):
    """La API excedió el tiempo máximo de espera."""


class ApiAuthenticationError(DataSourceError):
    """La API rechazó las credenciales."""


class ApiRateLimitError(DataSourceError):
    """Se alcanzó o se previno un límite de solicitudes."""
