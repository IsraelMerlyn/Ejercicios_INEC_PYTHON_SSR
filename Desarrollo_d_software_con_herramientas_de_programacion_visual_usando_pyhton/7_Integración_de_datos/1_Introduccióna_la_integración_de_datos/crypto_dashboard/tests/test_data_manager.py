from pathlib import Path

from repositories.data_manager import DataManager


def _sample_payload() -> list[dict[str, object]]:
    return [
        {
            "id": "bitcoin",
            "symbol": "btc",
            "name": "Bitcoin",
            "image": "https://example.com/bitcoin.png",
            "market_cap_rank": 1,
            "current_price": 68000.50,
            "market_cap": 1_300_000_000_000,
            "total_volume": 32_000_000_000,
            "price_change_percentage_24h": 2.5,
            "high_24h": 69000.0,
            "low_24h": 66000.0,
            "last_updated": "2026-07-10T18:30:45.123Z",
        }
    ]


def test_save_market_snapshot_avoids_duplicates(tmp_path: Path) -> None:
    manager = DataManager(tmp_path / "test.db")
    manager.initialize_database()

    first_result = manager.save_market_snapshot(_sample_payload(), "usd")
    second_result = manager.save_market_snapshot(_sample_payload(), "usd")

    assert first_result["inserted_records"] == 1
    assert second_result["inserted_records"] == 0
    assert second_result["ignored_duplicates"] == 1
    assert manager.count_price_records() == 1
