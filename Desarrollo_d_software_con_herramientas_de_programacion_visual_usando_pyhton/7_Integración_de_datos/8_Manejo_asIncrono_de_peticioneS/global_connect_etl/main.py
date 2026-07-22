"""Orquestador principal del ETL Global-Connect."""

from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import datetime, timezone
from typing import Any, Callable

from api_client import APIClient
from config import settings
from database import DatabaseManager
from exceptions import IntegrationError
from services.demo_api_server import DemoAPIServer
from services.finance_service import FinanceService
from services.identity_service import IdentityService
from services.weather_service import WeatherService
from transformers import merge_results, transform_assets, transform_users, transform_weather


def configure_logging() -> None:
    """Configura logging a consola y archivo local."""
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("logs/global_connect_etl.log", encoding="utf-8"),
        ],
    )


def utc_now_iso() -> str:
    """Devuelve la fecha actual en UTC con formato ISO 8601."""
    return datetime.now(timezone.utc).isoformat()


def safe_extract_and_transform(
    source_name: str,
    fetcher: Callable[[], dict[str, Any]],
    transformer: Callable[[dict[str, Any]], Any],
) -> Any:
    """Ejecuta extracción y transformación sin tumbar todo el ETL."""
    logger = logging.getLogger("global_connect.main")
    try:
        payload = fetcher()
        logger.info("source_payload_ready source=%s", source_name)
        return transformer(payload)
    except IntegrationError as exc:
        logger.error("source_failed source=%s error=%s", source_name, exc)
        # Si un proveedor falla, regresamos resultado vacío para degradar con elegancia.
        empty_result = transformer({"data": []})
        empty_result.add_error(source_name, "SOURCE_FAILURE", exc, {"source": source_name})
        return empty_result


def run_etl(limit: int, reset_db: bool, chaos: bool, empty: bool) -> dict[str, Any]:
    """Ejecuta el flujo ETL completo: extraer, transformar y cargar."""
    logger = logging.getLogger("global_connect.main")
    started = time.perf_counter()
    started_at_utc = utc_now_iso()
    demo_server: DemoAPIServer | None = None

    if settings.demo_server_enabled:
        demo_server = DemoAPIServer(port=8765)
        demo_server.start()
        time.sleep(0.15)
        logger.info("demo_server_started url=%s", settings.base_url)

    try:
        client = APIClient(
            base_url=settings.base_url,
            bearer_token=settings.bearer_token,
            api_key=settings.api_key,
            timeout=settings.request_timeout,
            max_retries=settings.max_retries,
            backoff_base_seconds=settings.backoff_base_seconds,
            cache_ttl_seconds=settings.cache_ttl_seconds,
        )

        identity_service = IdentityService(client)
        finance_service = FinanceService(client)
        weather_service = WeatherService(client)

        database = DatabaseManager(settings.database_path)
        database.initialize_schema(reset=reset_db)

        user_result = safe_extract_and_transform(
            "users",
            lambda: identity_service.fetch_users(limit=limit, chaos=chaos, empty=empty),
            transform_users,
        )
        asset_result = safe_extract_and_transform(
            "assets",
            lambda: finance_service.fetch_assets(limit=limit, chaos=chaos, empty=empty),
            transform_assets,
        )
        weather_result = safe_extract_and_transform(
            "weather",
            lambda: weather_service.fetch_weather(limit=limit, chaos=chaos, empty=empty),
            transform_weather,
        )

        merged = merge_results([user_result, asset_result, weather_result])
        counters = database.load_all(merged.records, merged.errors)

        total_success = sum(
            len(records) for table, records in merged.records.items() if table != "etl_errors"
        )
        total_failed = len(merged.errors)
        total_processed = total_success + total_failed
        elapsed_seconds = time.perf_counter() - started
        finished_at_utc = utc_now_iso()

        database.record_run(
            started_at_utc=started_at_utc,
            finished_at_utc=finished_at_utc,
            total_processed=total_processed,
            total_success=total_success,
            total_failed=total_failed,
            elapsed_seconds=elapsed_seconds,
        )

        report = {
            "total_processed": total_processed,
            "total_success": total_success,
            "total_failed": total_failed,
            "elapsed_seconds": round(elapsed_seconds, 4),
            "counters": counters,
        }
        logger.info("etl_finished report=%s", report)
        return report
    finally:
        if demo_server:
            demo_server.stop()
            logger.info("demo_server_stopped")


def build_parser() -> argparse.ArgumentParser:
    """Construye el parser de argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(description="ETL Global-Connect con APIs REST y SQLite")
    parser.add_argument("--limit", type=int, default=50, help="Cantidad de registros por endpoint")
    parser.add_argument("--reset-db", action="store_true", help="Recrear la base de datos desde cero")
    parser.add_argument("--chaos", action="store_true", help="Activa fallos aleatorios del proveedor demo")
    parser.add_argument("--empty", action="store_true", help="Simula respuestas JSON vacías")
    return parser


def main() -> None:
    """Punto de entrada del programa."""
    configure_logging()
    args = build_parser().parse_args()
    report = run_etl(
        limit=args.limit,
        reset_db=args.reset_db,
        chaos=args.chaos,
        empty=args.empty,
    )

    print("\nReporte final de ejecución")
    print("-" * 32)
    print(f"Total procesados : {report['total_processed']}")
    print(f"Total exitosos   : {report['total_success']}")
    print(f"Total fallidos   : {report['total_failed']}")
    print(f"Tiempo total     : {report['elapsed_seconds']} segundos")
    print("\nRegistros por tabla")
    for table, count in report["counters"].items():
        print(f"- {table}: {count}")


if __name__ == "__main__":
    main()
