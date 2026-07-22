from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from utils.exceptions import DataSourceError


@dataclass(frozen=True, slots=True)
class FetchResult:
    data: list[dict[str, Any]]
    from_cache: bool
    failed_resources: tuple[str, ...]


class PokeAPIClient:
    """Cliente REST con timeout, reintentos, caché y pausa entre solicitudes."""

    def __init__(
        self,
        base_url: str,
        timeout_seconds: int = 20,
        cache_ttl_seconds: int = 3600,
        minimum_request_interval_seconds: float = 0.10,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.cache_ttl_seconds = cache_ttl_seconds
        self.minimum_request_interval_seconds = minimum_request_interval_seconds
        self._cache: dict[tuple[int, int], tuple[float, list[dict[str, Any]]]] = {}
        self._last_request_at = 0.0

        retry = Retry(
            total=3,
            connect=3,
            read=3,
            backoff_factor=0.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"GET"}),
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": "PokemonDataLab/1.0 educational-project",
            }
        )
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def _wait_if_needed(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        pending = self.minimum_request_interval_seconds - elapsed
        if pending > 0:
            time.sleep(pending)

    def _get_json(
        self,
        url: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._wait_if_needed()
        try:
            response = self.session.get(
                url,
                params=params,
                timeout=self.timeout_seconds,
            )
            self._last_request_at = time.monotonic()
            response.raise_for_status()
        except requests.Timeout as exc:
            raise DataSourceError("PokéAPI tardó demasiado en responder.") from exc
        except requests.ConnectionError as exc:
            raise DataSourceError(
                "No fue posible conectarse con PokéAPI. Revisa tu internet."
            ) from exc
        except requests.HTTPError as exc:
            status_code = exc.response.status_code if exc.response else "desconocido"
            raise DataSourceError(
                f"PokéAPI respondió con un error HTTP {status_code}."
            ) from exc

        try:
            payload = response.json()
        except requests.JSONDecodeError as exc:
            raise DataSourceError("PokéAPI devolvió un JSON inválido.") from exc

        if not isinstance(payload, dict):
            raise DataSourceError("La respuesta de PokéAPI no es un objeto JSON.")
        return payload

    def fetch_pokemon(
        self,
        limit: int = 20,
        offset: int = 0,
        force_refresh: bool = False,
    ) -> FetchResult:
        if not 1 <= limit <= 100:
            raise ValueError("limit debe estar entre 1 y 100.")
        if offset < 0:
            raise ValueError("offset no puede ser negativo.")

        cache_key = (limit, offset)
        cached = self._cache.get(cache_key)
        if cached and not force_refresh:
            cached_at, cached_data = cached
            if time.monotonic() - cached_at < self.cache_ttl_seconds:
                return FetchResult(
                    data=list(cached_data),
                    from_cache=True,
                    failed_resources=(),
                )

        list_payload = self._get_json(
            f"{self.base_url}/pokemon",
            params={"limit": limit, "offset": offset},
        )
        resources = list_payload.get("results")
        if not isinstance(resources, list):
            raise DataSourceError("PokéAPI no devolvió la lista results esperada.")

        pokemon_data: list[dict[str, Any]] = []
        failed_resources: list[str] = []

        for resource in resources:
            if not isinstance(resource, dict):
                continue
            url = str(resource.get("url") or "").strip()
            name = str(resource.get("name") or url or "desconocido")
            if not url:
                failed_resources.append(name)
                continue
            try:
                pokemon_data.append(self._get_json(url))
            except DataSourceError:
                failed_resources.append(name)

        if not pokemon_data:
            raise DataSourceError(
                "No se pudo descargar ningún Pokémon desde la API."
            )

        self._cache[cache_key] = (time.monotonic(), list(pokemon_data))
        return FetchResult(
            data=pokemon_data,
            from_cache=False,
            failed_resources=tuple(failed_resources),
        )
