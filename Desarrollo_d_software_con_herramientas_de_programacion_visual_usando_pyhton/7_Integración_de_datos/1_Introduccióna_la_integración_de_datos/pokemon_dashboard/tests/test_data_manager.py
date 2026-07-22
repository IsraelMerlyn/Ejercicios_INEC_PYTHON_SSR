from pathlib import Path

from repositories.data_manager import DataManager, _build_demo_payloads


def test_save_pokemon_batch_upserts_without_duplicates(tmp_path: Path) -> None:
    manager = DataManager(tmp_path / "test.db")
    manager.initialize_database()
    payload = [_build_demo_payloads()[0]]

    first = manager.save_pokemon_batch(payload)
    second = manager.save_pokemon_batch(payload)

    assert first["inserted_records"] == 1
    assert first["updated_records"] == 0
    assert second["inserted_records"] == 0
    assert second["updated_records"] == 1
    assert manager.count_pokemon() == 1

    dataframe = manager.get_pokemon_data()
    assert dataframe.iloc[0]["name"] == "Bulbasaur"
    assert "grass" in dataframe.iloc[0]["types"]
    assert dataframe.iloc[0]["attack"] == 49
