from unittest.mock import Mock

import pytest
import requests

import api_client
from api_client import APIClient
from exceptions import (
    APIClientError,
    APIConnectionError,
    InvalidResponseFormat,
)


class FakeResponse:
    def __init__(self, status_code, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


def build_client(session, **kwargs):
    return APIClient(
        base_url="https://provider.test",
        service_name="test",
        max_retries=kwargs.get("max_retries", 2),
        backoff_factor=0,
        jitter_seconds=0,
        rate_limit_per_minute=0,
        session=session,
        default_headers=kwargs.get("headers"),
    )


def test_retry_on_500_then_success(monkeypatch):
    session = Mock()
    session.request.side_effect = [
        FakeResponse(500, {"error": "temporary"}, text="temporary"),
        FakeResponse(200, {"ok": True}),
    ]
    monkeypatch.setattr(api_client.time, "sleep", lambda _: None)
    client = build_client(session)

    result = client.get("/resource")

    assert result == {"ok": True}
    assert session.request.call_count == 2


def test_does_not_retry_permanent_404(monkeypatch):
    session = Mock()
    session.request.return_value = FakeResponse(404, {"error": "missing"}, text="missing")
    monkeypatch.setattr(api_client.time, "sleep", lambda _: None)
    client = build_client(session)

    with pytest.raises(APIClientError):
        client.get("/missing")

    assert session.request.call_count == 1


def test_timeout_raises_connection_error_after_retries(monkeypatch):
    session = Mock()
    session.request.side_effect = requests.exceptions.Timeout("slow")
    monkeypatch.setattr(api_client.time, "sleep", lambda _: None)
    client = build_client(session, max_retries=1)

    with pytest.raises(APIConnectionError):
        client.get("/slow")

    assert session.request.call_count == 2


def test_invalid_json_raises_custom_exception(monkeypatch):
    session = Mock()
    session.request.return_value = FakeResponse(200, ValueError("invalid"), text="not-json")
    monkeypatch.setattr(api_client.time, "sleep", lambda _: None)
    client = build_client(session)

    with pytest.raises(InvalidResponseFormat):
        client.get("/broken-json")


def test_cache_reuses_payload(monkeypatch):
    session = Mock()
    session.request.return_value = FakeResponse(200, {"value": 1})
    monkeypatch.setattr(api_client.time, "sleep", lambda _: None)
    client = build_client(session)

    first = client.get("/cached", use_cache=True, cache_ttl_seconds=60)
    second = client.get("/cached", use_cache=True, cache_ttl_seconds=60)

    assert first == second == {"value": 1}
    assert session.request.call_count == 1


def test_credentials_are_not_exposed_in_error_logs(monkeypatch, caplog):
    secret = "secret-token-123456"
    session = Mock()
    session.request.return_value = FakeResponse(500, {"error": "bad"}, text=f"token={secret}")
    monkeypatch.setattr(api_client.time, "sleep", lambda _: None)
    client = build_client(session, max_retries=0, headers={"Authorization": secret})

    with pytest.raises(Exception):
        client.get("/unstable")

    assert secret not in caplog.text
