"""Pruebas del cliente HTTP base con mocks de requests."""

from __future__ import annotations

from typing import Any

import pytest
import requests

from api_client import APIClient
from exceptions import APIResponseError, InvalidResponseFormat


class FakeResponse:
    """Respuesta falsa compatible con las partes usadas de requests.Response."""

    def __init__(self, status_code: int, payload: Any = None, text: str = "") -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = text or str(payload)

    def json(self) -> Any:
        if self._payload == "INVALID_JSON":
            raise ValueError("invalid json")
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


def test_retry_en_error_500_y_luego_exito(monkeypatch: pytest.MonkeyPatch) -> None:
    """Valida que el cliente reintente ante 500 y luego recupere."""
    client = APIClient("http://example.test", max_retries=3, backoff_base_seconds=0)
    calls = {"count": 0}

    def fake_request(*args: Any, **kwargs: Any) -> FakeResponse:
        calls["count"] += 1
        if calls["count"] == 1:
            return FakeResponse(500, {"error": "server"})
        return FakeResponse(200, {"ok": True})

    monkeypatch.setattr(client.session, "request", fake_request)
    monkeypatch.setattr("api_client.time.sleep", lambda seconds: None)

    data = client.get("/resource", use_cache=False)

    assert data == {"ok": True}
    assert calls["count"] == 2


def test_no_reintenta_error_404(monkeypatch: pytest.MonkeyPatch) -> None:
    """Valida que un 404 no se reintente porque es error permanente."""
    client = APIClient("http://example.test", max_retries=3, backoff_base_seconds=0)
    calls = {"count": 0}

    def fake_request(*args: Any, **kwargs: Any) -> FakeResponse:
        calls["count"] += 1
        return FakeResponse(404, {"error": "not found"})

    monkeypatch.setattr(client.session, "request", fake_request)

    with pytest.raises(APIResponseError):
        client.get("/missing", use_cache=False)

    assert calls["count"] == 1


def test_json_invalido_lanza_excepcion_controlada(monkeypatch: pytest.MonkeyPatch) -> None:
    """Valida que JSON inválido se traduzca a una excepción del dominio."""
    client = APIClient("http://example.test", max_retries=1, backoff_base_seconds=0)

    def fake_request(*args: Any, **kwargs: Any) -> FakeResponse:
        return FakeResponse(200, "INVALID_JSON", text="{invalid-json")

    monkeypatch.setattr(client.session, "request", fake_request)

    with pytest.raises(InvalidResponseFormat):
        client.get("/broken", use_cache=False)


def test_cache_evita_segunda_llamada(monkeypatch: pytest.MonkeyPatch) -> None:
    """Valida que el caché reduzca llamadas repetidas al mismo endpoint."""
    client = APIClient("http://example.test", cache_ttl_seconds=60)
    calls = {"count": 0}

    def fake_request(*args: Any, **kwargs: Any) -> FakeResponse:
        calls["count"] += 1
        return FakeResponse(200, {"items": [1, 2, 3]})

    monkeypatch.setattr(client.session, "request", fake_request)

    assert client.get("/items") == {"items": [1, 2, 3]}
    assert client.get("/items") == {"items": [1, 2, 3]}
    assert calls["count"] == 1
