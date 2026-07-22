"""Local HTTP demo provider used to run the project without paid APIs."""

from __future__ import annotations

import json
import random
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional
from urllib.parse import parse_qs, urlparse

DRIVERS = {
    "D-1001": {
        "driverId": "D-1001",
        "profile": {"fullName": "ana martinez"},
        "compliance": {
            "licenseStatus": "ACTIVE",
            "verified": True,
            "riskScore": 0.08,
        },
    },
    "D-1002": {
        "driverId": "D-1002",
        "profile": {"fullName": "luis garcia"},
        "compliance": {
            "licenseStatus": "ACTIVE",
            "verified": True,
            "riskScore": 0.18,
        },
    },
    "D-1003": {
        "driverId": "D-1003",
        "profile": {"fullName": "maria lopez"},
        "compliance": {
            "licenseStatus": "REVIEW",
            "verified": False,
            "riskScore": 0.42,
        },
    },
}

VEHICLES = {
    "V-1001": {
        "vehicleId": "V-1001",
        "driverId": "D-1001",
        "location": {"coordinates": {"lat": "19.4326", "lon": "-99.1332"}},
        "speedKmh": "42.5",
        "status": "IN_TRANSIT",
    },
    "V-1002": {
        "vehicleId": "V-1002",
        "driverId": "D-1002",
        "location": {"coordinates": {"lat": "20.6597", "lon": "-103.3496"}},
        "speedKmh": 0,
        "status": "STOPPED",
    },
    "V-1003": {
        "vehicleId": "V-1003",
        "driverId": "D-1003",
        "location": {"coordinates": {"lat": "17.0608", "lon": "-96.7253"}},
        "speedKmh": "63.1",
        "status": "IN_TRANSIT",
    },
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class DemoProviderHandler(BaseHTTPRequestHandler):
    """Tiny provider with three simulated external APIs."""

    chaos_mode = False

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        return

    def do_GET(self) -> None:  # noqa: N802
        if self._maybe_fail_with_chaos():
            return

        parsed = urlparse(self.path)
        if parsed.path.startswith("/fleet/vehicles/") and parsed.path.endswith("/location"):
            vehicle_id = parsed.path.split("/")[3]
            payload = VEHICLES.get(vehicle_id)
            if payload is None:
                self._send_json(404, {"error": "vehicle_not_found"})
                return
            enriched = {**payload, "capturedAt": _now()}
            self._send_json(200, enriched)
            return

        if parsed.path == "/weather/current":
            query = parse_qs(parsed.query)
            lat = query.get("lat", ["0"])[0]
            lon = query.get("lon", ["0"])[0]
            temperature = 18.0 + random.random() * 12
            condition = random.choice(["clear", "cloudy", "rain", "windy"])
            self._send_json(
                200,
                {
                    "location": {
                        "city": self._city_for_lat(lat),
                        "lat": lat,
                        "lon": lon,
                    },
                    "measurements": {
                        "temp_celsius": round(temperature, 2),
                        "condition": condition,
                    },
                    "observedAt": _now(),
                },
            )
            return

        self._send_json(404, {"error": "unknown_endpoint"})

    def do_POST(self) -> None:  # noqa: N802
        if self._maybe_fail_with_chaos():
            return

        parsed = urlparse(self.path)
        if parsed.path == "/identity/verify":
            body = self._read_json_body()
            driver_id = body.get("driver_id")
            payload = DRIVERS.get(str(driver_id))
            if payload is None:
                self._send_json(404, {"error": "driver_not_found"})
                return
            self._send_json(200, {**payload, "updatedAt": _now()})
            return

        self._send_json(404, {"error": "unknown_endpoint"})

    def _read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    def _maybe_fail_with_chaos(self) -> bool:
        if not self.chaos_mode:
            return False
        dice = random.random()
        if dice < 0.20:
            self._send_json(500, {"error": "simulated_server_error"})
            return True
        if dice < 0.35:
            time.sleep(1.5)
        if dice < 0.42:
            self._send_json(429, {"error": "simulated_rate_limit"})
            return True
        return False

    def _send_json(self, status: int, payload: dict) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _city_for_lat(self, latitude: str) -> str:
        try:
            lat = float(latitude)
        except ValueError:
            return "unknown"
        if lat > 20:
            return "Guadalajara"
        if lat > 18:
            return "Ciudad De Mexico"
        return "Oaxaca"


class DemoProviderServer:
    """Background server wrapper."""

    def __init__(self, host: str, port: int, chaos_mode: bool = False) -> None:
        self.host = host
        self.port = port
        self.chaos_mode = chaos_mode
        self._server: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> str:
        DemoProviderHandler.chaos_mode = self.chaos_mode
        self._server = ThreadingHTTPServer((self.host, self.port), DemoProviderHandler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return f"http://{self.host}:{self.port}"

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
            self._server.server_close()
        if self._thread:
            self._thread.join(timeout=2)
