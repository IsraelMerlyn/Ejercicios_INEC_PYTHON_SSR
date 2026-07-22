"""Cliente HTTP base con sesión persistente, retries, caché y logging."""

from __future__ import annotations

import json
import logging
import random
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin

import requests

from exceptions import (
    APIConnectionError,
    APIRateLimitExceeded,
    APIResponseError,
    InvalidResponseFormat,
)

logger = logging.getLogger("global_connect.integration")


@dataclass
class CacheItem:
    """Elemento simple para caché en memoria con tiempo de expiración."""

    expires_at: float
    data: Any


class APIClient:
    """
    Cliente HTTP genérico para proveedores REST.

    Esta clase centraliza la lógica transversal del consumo HTTP:
    sesión persistente, headers comunes, autenticación, retries,
    backoff exponencial, jitter, caché y traducción de errores.
    """

    RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

    def __init__(
        self,
        base_url: str,
        bearer_token: str | None = None,
        api_key: str | None = None,
        timeout: float = 10.0,
        max_retries: int = 3,
        backoff_base_seconds: float = 0.5,
        cache_ttl_seconds: int = 60,
    ) -> None:
        self.base_url = base_url.rstrip("/") + "/"
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_base_seconds = backoff_base_seconds
        self.cache_ttl_seconds = cache_ttl_seconds
        self.session = requests.Session()
        self.cache: dict[str, CacheItem] = {}

        # Estos headers aplican a todos los proveedores simulados del ejercicio.
        self.session.headers.update(
            {
                "User-Agent": "GlobalConnectETL/1.0",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )

        if bearer_token:
            self.session.headers["Authorization"] = f"Bearer {bearer_token}"
        if api_key:
            self.session.headers["X-API-Key"] = api_key

    def get(self, endpoint: str, params: dict[str, Any] | None = None, use_cache: bool = True) -> Any:
        """Ejecuta una petición GET y devuelve el JSON deserializado."""
        return self.request("GET", endpoint, params=params, use_cache=use_cache)

    def post(self, endpoint: str, payload: dict[str, Any] | None = None) -> Any:
        """Ejecuta una petición POST con payload JSON."""
        return self.request("POST", endpoint, json_payload=payload, use_cache=False)

    def request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json_payload: dict[str, Any] | None = None,
        use_cache: bool = True,
    ) -> Any:
        """Ejecuta una petición HTTP con retry inteligente."""
        url = urljoin(self.base_url, endpoint.lstrip("/"))
        cache_key = self._build_cache_key(method, url, params, json_payload)

        if method.upper() == "GET" and use_cache:
            cached = self._get_from_cache(cache_key)
            if cached is not None:
                logger.info("cache_hit method=%s url=%s", method.upper(), url)
                return cached

        last_exception: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            started_at = time.perf_counter()
            try:
                response = self.session.request(
                    method=method.upper(),
                    url=url,
                    params=params,
                    json=json_payload,
                    timeout=self.timeout,
                )
                elapsed_ms = (time.perf_counter() - started_at) * 1000

                logger.info(
                    "http_request method=%s url=%s status=%s elapsed_ms=%.2f attempt=%s",
                    method.upper(),
                    url,
                    response.status_code,
                    elapsed_ms,
                    attempt,
                )

                if response.status_code == 429 and attempt >= self.max_retries:
                    raise APIRateLimitExceeded("La API respondió 429 después de varios intentos")

                if response.status_code in self.RETRYABLE_STATUS_CODES:
                    self._wait_before_retry(attempt)
                    continue

                if 400 <= response.status_code < 500:
                    body = self._safe_response_text(response)
                    raise APIResponseError(
                        f"Error HTTP permanente {response.status_code}. Body: {body}"
                    )

                response.raise_for_status()
                data = self._parse_json(response)

                if method.upper() == "GET" and use_cache:
                    self._save_in_cache(cache_key, data)

                return data

            except (requests.Timeout, requests.ConnectionError) as exc:
                last_exception = exc
                logger.warning(
                    "network_retry method=%s url=%s attempt=%s error=%s",
                    method.upper(),
                    url,
                    attempt,
                    exc.__class__.__name__,
                )
                if attempt >= self.max_retries:
                    break
                self._wait_before_retry(attempt)

        raise APIConnectionError(f"No fue posible consumir {url}: {last_exception}")

    def _parse_json(self, response: requests.Response) -> Any:
        """Convierte la respuesta a JSON y falla de forma controlada si no es válida."""
        try:
            return response.json()
        except ValueError as exc:
            raise InvalidResponseFormat("La API devolvió una respuesta que no es JSON válido") from exc

    def _wait_before_retry(self, attempt: int) -> None:
        """Aplica backoff exponencial con jitter para evitar el efecto trueno."""
        delay = self.backoff_base_seconds * (2 ** (attempt - 1))
        jitter = random.uniform(0, self.backoff_base_seconds)
        time.sleep(delay + jitter)

    def _build_cache_key(
        self,
        method: str,
        url: str,
        params: dict[str, Any] | None,
        json_payload: dict[str, Any] | None,
    ) -> str:
        """Construye una llave determinista para el caché de GET."""
        raw_key = {
            "method": method.upper(),
            "url": url,
            "params": params or {},
            "payload": json_payload or {},
        }
        return json.dumps(raw_key, sort_keys=True, default=str)

    def _get_from_cache(self, cache_key: str) -> Any | None:
        """Obtiene un valor del caché si no ha expirado."""
        item = self.cache.get(cache_key)
        if not item:
            return None
        if item.expires_at < time.time():
            del self.cache[cache_key]
            return None
        return item.data

    def _save_in_cache(self, cache_key: str, data: Any) -> None:
        """Guarda la respuesta en memoria por el TTL configurado."""
        self.cache[cache_key] = CacheItem(
            expires_at=time.time() + self.cache_ttl_seconds,
            data=data,
        )

    def _safe_response_text(self, response: requests.Response) -> str:
        """Devuelve un cuerpo seguro para logs sin exponer credenciales."""
        text = response.text[:500]
        for header_name in ("Authorization", "X-API-Key"):
            secret = self.session.headers.get(header_name)
            if secret:
                text = text.replace(secret, "***MASKED***")
        return text
