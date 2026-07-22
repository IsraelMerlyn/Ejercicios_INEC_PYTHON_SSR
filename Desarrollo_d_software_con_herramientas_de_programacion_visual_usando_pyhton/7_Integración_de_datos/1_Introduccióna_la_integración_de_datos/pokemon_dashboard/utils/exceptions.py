class DataSourceError(RuntimeError):
    """Error controlado al consultar una fuente de datos externa."""


class DataValidationError(ValueError):
    """Error controlado cuando el JSON no cumple el contrato esperado."""
