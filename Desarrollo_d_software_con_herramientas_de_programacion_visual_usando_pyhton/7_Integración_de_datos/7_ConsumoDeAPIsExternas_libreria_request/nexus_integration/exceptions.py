"""Custom exception hierarchy for Nexus Logistics integrations."""


class IntegrationError(Exception):
    """Base exception for all integration-layer failures."""


class APIConnectionError(IntegrationError):
    """Raised when a provider cannot be reached after all retries."""


class APIRateLimitExceeded(IntegrationError):
    """Raised when a provider keeps responding with HTTP 429."""


class APIServerError(IntegrationError):
    """Raised when a provider keeps returning transient 5xx errors."""


class APIClientError(IntegrationError):
    """Raised for permanent HTTP 4xx errors that should not be retried."""


class APIAuthenticationError(APIClientError):
    """Raised when the provider rejects credentials or permissions."""


class InvalidResponseFormat(IntegrationError):
    """Raised when a provider returns malformed or unexpected JSON."""


class DataValidationError(IntegrationError):
    """Raised when transformed provider data violates internal rules."""
