"""Main orchestration script for Operación Puente de Datos."""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

from config import Settings, load_settings
from database import NexusRepository
from exceptions import IntegrationError
from models import SyncReport
from services.demo_provider import DemoProviderServer
from services.fleet_service import FleetService
from services.identity_service import IdentityService
from services.weather_service import WeatherService


def configure_logging(level: str) -> None:
    """Configure console and file logging."""

    Path("logs").mkdir(exist_ok=True)
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("logs/integration.log", encoding="utf-8"),
        ],
    )


def split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def run_pipeline(settings: Settings) -> SyncReport:
    """Execute the integration pipeline with graceful degradation."""

    logger = logging.getLogger("integration.main")
    demo_server: Optional[DemoProviderServer] = None

    if settings.demo_provider_enabled:
        demo_server = DemoProviderServer(
            settings.demo_provider_host,
            settings.demo_provider_port,
            chaos_mode=settings.chaos_mode,
        )
        demo_url = demo_server.start()
        logger.info("demo_provider_started url=%s chaos_mode=%s", demo_url, settings.chaos_mode)

    repository = NexusRepository(settings.database_name)
    repository.initialize_schema()
    report = SyncReport()
    started_at = datetime.now(timezone.utc).isoformat()

    try:
        identity = IdentityService(settings.resolve_base_url(settings.identity_base_url), settings)
        fleet = FleetService(settings.resolve_base_url(settings.fleet_base_url), settings)
        weather = WeatherService(settings.resolve_base_url(settings.weather_base_url), settings)

        _sync_drivers(split_csv(settings.driver_ids), identity, repository, report)
        _sync_fleet_and_weather(split_csv(settings.vehicle_ids), fleet, weather, repository, report)

    finally:
        finished_at = datetime.now(timezone.utc).isoformat()
        repository.save_sync_run(
            started_at=started_at,
            finished_at=finished_at,
            processed=report.processed,
            failed=report.failed,
            skipped=report.skipped,
            notes="Run completed with graceful degradation",
        )
        logger.info(
            "sync_report processed=%s failed=%s skipped=%s total=%s",
            report.processed,
            report.failed,
            report.skipped,
            report.total,
        )
        logger.info(
            "db_counts drivers=%s positions=%s weather=%s runs=%s",
            repository.count_rows("drivers"),
            repository.count_rows("vehicle_positions"),
            repository.count_rows("weather_snapshots"),
            repository.count_rows("sync_runs"),
        )
        repository.close()
        if demo_server:
            demo_server.stop()

    return report


def _sync_drivers(
    driver_ids: Iterable[str],
    identity: IdentityService,
    repository: NexusRepository,
    report: SyncReport,
) -> None:
    logger = logging.getLogger("integration.identity_pipeline")
    for driver_id in driver_ids:
        try:
            driver = identity.verify_driver(driver_id)
            repository.save_driver(driver)
            report.register_success()
            logger.info("driver_verified driver_id=%s verified=%s", driver.driver_id, driver.verified)
        except IntegrationError as exc:
            report.register_failure()
            logger.error("driver_sync_failed driver_id=%s reason=%s", driver_id, exc)


def _sync_fleet_and_weather(
    vehicle_ids: Iterable[str],
    fleet: FleetService,
    weather: WeatherService,
    repository: NexusRepository,
    report: SyncReport,
) -> None:
    logger = logging.getLogger("integration.fleet_pipeline")
    for vehicle_id in vehicle_ids:
        try:
            position = fleet.get_vehicle_position(vehicle_id)
            repository.save_position(position)
            report.register_success()
            logger.info(
                "position_saved vehicle_id=%s driver_id=%s lat=%s lon=%s",
                position.vehicle_id,
                position.driver_id,
                position.latitude,
                position.longitude,
            )
        except IntegrationError as exc:
            report.register_failure()
            logger.error("position_sync_failed vehicle_id=%s reason=%s", vehicle_id, exc)
            continue

        try:
            snapshot = weather.get_current_weather(position.latitude, position.longitude)
            repository.save_weather(snapshot)
            report.register_success()
            logger.info(
                "weather_saved vehicle_id=%s city=%s temp_c=%s",
                vehicle_id,
                snapshot.city,
                snapshot.temperature_c,
            )
        except IntegrationError as exc:
            report.register_skip()
            logger.error(
                "weather_sync_degraded vehicle_id=%s reason=%s action=continue",
                vehicle_id,
                exc,
            )


def main() -> None:
    settings = load_settings()
    configure_logging(settings.log_level)
    report = run_pipeline(settings)
    print("\nReporte final")
    print(f"Procesados: {report.processed}")
    print(f"Fallidos: {report.failed}")
    print(f"Omitidos por degradación: {report.skipped}")
    print(f"Total evaluado: {report.total}")


if __name__ == "__main__":
    main()
