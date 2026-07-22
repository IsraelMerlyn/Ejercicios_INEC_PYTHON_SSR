"""Servidor HTTP local que simula tres proveedores externos."""

from __future__ import annotations

import json
import random
import threading
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

FIRST_NAMES = [
    "ana", "bruno", "carla", "diego", "elena", "franco", "gabriela", "hector",
    "irene", "jorge", "karla", "luis", "mariana", "nicolas", "olivia", "pablo",
]
LAST_NAMES = [
    "lopez", "martinez", "garcia", "hernandez", "vazquez", "santos", "ramirez", "cruz",
]
CITIES = [
    ("Mexico City", "MX", "19.4326", "-99.1332"),
    ("Monterrey", "MX", "25.6866", "-100.3161"),
    ("Guadalajara", "MX", "20.6597", "-103.3496"),
    ("Oaxaca", "MX", "17.0732", "-96.7266"),
    ("Bogota", "CO", "4.7110", "-74.0721"),
    ("Lima", "PE", "-12.0464", "-77.0428"),
]
SECTORS = ["technology", "health", "finance", "energy", "retail"]
CONDITIONS = ["clear", "cloudy", "rain", "storm", "fog"]


def make_iso(days_offset: int, hours_offset: int = 0) -> str:
    """Genera fechas ISO 8601 estables en UTC."""
    value = datetime(2026, 7, 21, 12, 0, tzinfo=timezone.utc)
    value = value - timedelta(days=days_offset, hours=hours_offset)
    return value.isoformat().replace("+00:00", "Z")


def build_users(limit: int) -> dict[str, Any]:
    """Construye usuarios con JSON anidado y listas de suscripciones."""
    data = []
    for index in range(1, limit + 1):
        city, country, lat, lon = CITIES[index % len(CITIES)]
        first = FIRST_NAMES[index % len(FIRST_NAMES)]
        last = LAST_NAMES[index % len(LAST_NAMES)]
        data.append(
            {
                "id": f"usr_{index:04d}",
                "profile": {
                    "name": {"first": first, "last": last},
                    "email": f"{first}.{last}{index}@global-connect.test",
                    "status": "active" if index % 5 else "inactive",
                    "created_at": make_iso(index),
                    "address": {
                        "city": city,
                        "country": country,
                        "geo": {"lat": lat, "lng": lon},
                    },
                },
                "subscriptions": [
                    {
                        "plan": "premium" if index % 3 == 0 else "standard",
                        "price_usd": f"{9.99 + (index % 5) * 4:.2f}",
                        "active": index % 5 != 0,
                        "started_at": make_iso(index + 30),
                    }
                ],
            }
        )
    return {"data": data, "meta": {"count": len(data), "provider": "identity-demo"}}


def build_assets(limit: int) -> dict[str, Any]:
    """Construye activos con anidación profunda data -> attributes -> history -> values."""
    data = []
    for index in range(1, limit + 1):
        history = []
        for day in range(5):
            base_price = 20 + index * 1.7
            history.append(
                {
                    "timestamp": make_iso(day),
                    "price_usd": f"{base_price + day * 0.35:.2f}",
                    "volume": f"{1000 + index * 50 + day * 10:.2f}",
                }
            )
        data.append(
            {
                "id": f"asset_{index:04d}",
                "attributes": {
                    "symbol": f"GC{index:03d}",
                    "name": f"Global Connect Asset {index}",
                    "listed_at": make_iso(index + 100),
                    "market": {
                        "sector": SECTORS[index % len(SECTORS)],
                        "currency": "USD",
                    },
                    "history": {"values": history},
                },
            }
        )
    return {"data": data, "meta": {"count": len(data), "provider": "finance-demo"}}


def build_weather(limit: int) -> dict[str, Any]:
    """Construye datos climáticos con observación actual y pronóstico."""
    data = []
    for index in range(1, limit + 1):
        city, country, lat, lon = CITIES[index % len(CITIES)]
        forecast = []
        for day in range(3):
            forecast.append(
                {
                    "date": (datetime(2026, 7, 21) + timedelta(days=day)).date().isoformat(),
                    "min_temp_c": f"{14 + index % 8 + day:.1f}",
                    "max_temp_c": f"{24 + index % 9 + day:.1f}",
                    "rain_probability": f"{(index * 7 + day * 3) % 100}",
                }
            )
        data.append(
            {
                "id": f"city_{index:04d}",
                "location": {
                    "city": f"{city} Zone {index}",
                    "country": country,
                    "coordinates": {"lat": lat, "lon": lon},
                },
                "current": {
                    "temp_celsius": f"{18 + index % 12:.1f}",
                    "humidity": str(40 + index % 50),
                    "condition": CONDITIONS[index % len(CONDITIONS)],
                    "observed_at": make_iso(index % 4),
                },
                "forecast": forecast,
            }
        )
    return {"data": data, "meta": {"count": len(data), "provider": "weather-demo"}}


class DemoRequestHandler(BaseHTTPRequestHandler):
    """Manejador HTTP mínimo para simular endpoints REST."""

    server_version = "GlobalConnectDemo/1.0"

    def do_GET(self) -> None:  # noqa: N802 - nombre requerido por BaseHTTPRequestHandler
        """Atiende peticiones GET de los tres proveedores simulados."""
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        limit = int(query.get("limit", ["40"])[0])

        if query.get("empty", ["false"])[0].lower() == "true":
            self._send_json(200, {"data": [], "meta": {"count": 0}})
            return

        if query.get("fail", [""])[0] == "500":
            self._send_json(500, {"error": "simulated server error"})
            return

        if query.get("invalid_json", ["false"])[0].lower() == "true":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b"{invalid-json")
            return

        # El modo caos introduce fallos aleatorios para pruebas manuales.
        if query.get("chaos", ["false"])[0].lower() == "true" and random.random() < 0.15:
            self._send_json(random.choice([429, 500, 503]), {"error": "chaos failure"})
            return

        if parsed.path == "/api/v1/users":
            self._send_json(200, build_users(limit))
        elif parsed.path == "/api/v1/finance/assets":
            self._send_json(200, build_assets(limit))
        elif parsed.path == "/api/v1/weather/cities":
            self._send_json(200, build_weather(limit))
        else:
            self._send_json(404, {"error": "not found"})

    def log_message(self, format: str, *args: Any) -> None:
        """Silencia el log por defecto para que el log estructurado sea más limpio."""
        return

    def _send_json(self, status_code: int, payload: dict[str, Any]) -> None:
        """Envía una respuesta JSON con el código HTTP indicado."""
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class DemoAPIServer:
    """Servidor demo ejecutado en un hilo para pruebas locales."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8765) -> None:
        self.host = host
        self.port = port
        self.httpd = ThreadingHTTPServer((host, port), DemoRequestHandler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def start(self) -> None:
        """Inicia el servidor local."""
        self.thread.start()

    def stop(self) -> None:
        """Detiene el servidor local."""
        self.httpd.shutdown()
        self.thread.join(timeout=2)
