"""Reusable HTTP client with retries, backoff, jitter, cache and logging."""

from __future__ import annotations

import hashlib
import json
import logging
import random
import time
from abc import ABC
from typing import Any, Dict, Mapping, Optional, Tuple

import requests

from exceptions import (
    APIAuthenticationError,
    APIClientError,
    APIConnectionError,
    APIRateLimitExceeded,
    APIServerError,
    InvalidResponseFormat,
)

SENSITIVE_HEADER_NAMES = {
    "authorization",
    "proxy-authorization",
    "x-api-key",
    "x-identity-key",
    "x-cg-demo-api-key",
    "api-key",
    "apikey",
    "token",
}


class APIClient(ABC):
    """
    Base client used by all provider-specific services.

    This class is intentionally infrastructure-only. Business rules live in
    service adapters and models so external JSON contracts do not leak into the
    rest of the application.
    """

    retryable_statuses = {429, 500, 502, 503, 504}

    def __init__(
        self,
        base_url: str,
        service_name: str,
        default_headers: Optional[Mapping[str, str]] = None,
        timeout: Tuple[float, float] = (3.05, 10.0),
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        jitter_seconds: float = 0.25,
        cache_ttl_seconds: int = 300,
        rate_limit_per_minute: int = 60,
        session: Optional[requests.Session] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.service_name = service_name
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.jitter_seconds = jitter_seconds
        self.cache_ttl_seconds = cache_ttl_seconds
        self.rate_limit_per_minute = rate_limit_per_minute
        self.session = session or requests.Session()
        self.logger = logger or logging.getLogger(f"integration.{service_name}")
        self._cache: Dict[str, tuple[float, Any]] = {}
        self._last_request_at = 0.0

        self.default_headers = {
            "User-Agent": "NexusIntegration/1.0",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if default_headers:
            self.default_headers.update(default_headers)

    def get(
        self,
        path: str,
        params: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
        use_cache: bool = False,
        cache_ttl_seconds: Optional[int] = None,
    ) -> Any:
        """Execute a GET request."""

        return self.request(
            "GET",
            path,
            params=params,
            headers=headers,
            use_cache=use_cache,
            cache_ttl_seconds=cache_ttl_seconds,
        )

    def post(
        self,
        path: str,
        payload: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
        use_cache: bool = False,
        cache_ttl_seconds: Optional[int] = None,
    ) -> Any:
        """Execute a POST request with a JSON body."""

        return self.request(
            "POST",
            path,
            json_payload=payload,
            headers=headers,
            use_cache=use_cache,
            cache_ttl_seconds=cache_ttl_seconds,
        )

    def request(
        self,
        method: str,
        path: str,
        params: Optional[Mapping[str, Any]] = None,
        json_payload: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
        use_cache: bool = False,
        cache_ttl_seconds: Optional[int] = None,
    ) -> Any:
        """Execute an HTTP request with retry and optional TTL cache."""

        method = method.upper()
        url = self._build_url(path)
        request_headers = dict(self.default_headers)
        if headers:
            request_headers.update(headers)

        cache_key = self._make_cache_key(method, url, params, json_payload)
        ttl = cache_ttl_seconds or self.cache_ttl_seconds
        if use_cache:
            cached_value = self._get_cached_value(cache_key, ttl)
            if cached_value is not None:
                self.logger.info(
                    "cache_hit service=%s method=%s url=%s",
                    self.service_name,
                    method,
                    url,
                )
                return cached_value

        last_error: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 2):
            self._apply_rate_limit()
            started_at = time.monotonic()
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    headers=request_headers,
                    params=params,
                    json=json_payload,
                    timeout=self.timeout,
                )
                elapsed_ms = int((time.monotonic() - started_at) * 1000)
                self._log_response(method, url, response.status_code, elapsed_ms)

                if response.status_code in self.retryable_statuses:
                    last_error = self._build_retryable_error(response)
                    if attempt <= self.max_retries:
                        self._sleep_before_retry(attempt, response.status_code)
                        continue
                    raise last_error

                if 400 <= response.status_code < 500:
                    self._raise_client_error(response)

                payload = self._parse_json(response)
                if use_cache:
                    self._cache[cache_key] = (time.monotonic(), payload)
                return payload

            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
                last_error = exc
                elapsed_ms = int((time.monotonic() - started_at) * 1000)
                self.logger.warning(
                    "network_error service=%s method=%s url=%s attempt=%s "
                    "elapsed_ms=%s error_type=%s",
                    self.service_name,
                    method,
                    url,
                    attempt,
                    elapsed_ms,
                    type(exc).__name__,
                )
                if attempt <= self.max_retries:
                    self._sleep_before_retry(attempt, None)
                    continue
                raise APIConnectionError(
                    f"{self.service_name}: network failure after {attempt} attempts"
                ) from exc

        raise APIConnectionError(
            f"{self.service_name}: request failed unexpectedly: {last_error}"
        )

    def clear_cache(self) -> None:
        """Clear in-memory cache entries."""

        self._cache.clear()

    def _build_url(self, path: str) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path
        normalized = path if path.startswith("/") else f"/{path}"
        return f"{self.base_url}{normalized}"

    def _make_cache_key(
        self,
        method: str,
        url: str,
        params: Optional[Mapping[str, Any]],
        json_payload: Optional[Mapping[str, Any]],
    ) -> str:
        raw = json.dumps(
            {
                "method": method,
                "url": url,
                "params": params or {},
                "json": json_payload or {},
            },
            sort_keys=True,
            default=str,
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _get_cached_value(self, cache_key: str, ttl: int) -> Optional[Any]:
        item = self._cache.get(cache_key)
        if not item:
            return None
        created_at, payload = item
        if time.monotonic() - created_at <= ttl:
            return payload
        self._cache.pop(cache_key, None)
        return None

    def _apply_rate_limit(self) -> None:
        if self.rate_limit_per_minute <= 0:
            return
        min_interval = 60.0 / self.rate_limit_per_minute
        now = time.monotonic()
        elapsed = now - self._last_request_at
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        self._last_request_at = time.monotonic()

    def _sleep_before_retry(self, attempt: int, status_code: Optional[int]) -> None:
        delay = self.backoff_factor * (2 ** (attempt - 1))
        delay += random.uniform(0, self.jitter_seconds)
        self.logger.warning(
            "retry_scheduled service=%s attempt=%s next_delay=%.2f "
            "status_code=%s",
            self.service_name,
            attempt,
            delay,
            status_code,
        )
        time.sleep(delay)

    def _build_retryable_error(self, response: requests.Response) -> Exception:
        body = self._safe_body_excerpt(response)
        if response.status_code == 429:
            return APIRateLimitExceeded(
                f"{self.service_name}: rate limit exceeded. body={body}"
            )
        return APIServerError(
            f"{self.service_name}: transient server error "
            f"status={response.status_code}. body={body}"
        )

    def _raise_client_error(self, response: requests.Response) -> None:
        body = self._safe_body_excerpt(response)
        if response.status_code in {401, 403}:
            raise APIAuthenticationError(
                f"{self.service_name}: authentication/authorization failed "
                f"status={response.status_code}. body={body}"
            )
        raise APIClientError(
            f"{self.service_name}: permanent client error "
            f"status={response.status_code}. body={body}"
        )

    def _parse_json(self, response: requests.Response) -> Any:
        try:
            return response.json()
        except ValueError as exc:
            raise InvalidResponseFormat(
                f"{self.service_name}: response is not valid JSON"
            ) from exc

    def _log_response(
        self,
        method: str,
        url: str,
        status_code: int,
        elapsed_ms: int,
    ) -> None:
        self.logger.info(
            "http_response service=%s method=%s url=%s status=%s elapsed_ms=%s",
            self.service_name,
            method,
            url,
            status_code,
            elapsed_ms,
        )

    def _safe_body_excerpt(self, response: requests.Response, limit: int = 300) -> str:
        text = getattr(response, "text", "") or ""
        text = self._redact_text(text)
        if len(text) > limit:
            return f"{text[:limit]}..."
        return text

    def _redact_text(self, text: str) -> str:
        for value in self.default_headers.values():
            if value and len(value) >= 6:
                text = text.replace(value, "[REDACTED]")
        return text

    @staticmethod
    def sanitize_headers(headers: Mapping[str, str]) -> Dict[str, str]:
        """Return headers safe for logs or diagnostics."""

        safe: Dict[str, str] = {}
        for key, value in headers.items():
            if key.lower() in SENSITIVE_HEADER_NAMES:
                safe[key] = "[REDACTED]"
            else:
                safe[key] = value
        return safe
