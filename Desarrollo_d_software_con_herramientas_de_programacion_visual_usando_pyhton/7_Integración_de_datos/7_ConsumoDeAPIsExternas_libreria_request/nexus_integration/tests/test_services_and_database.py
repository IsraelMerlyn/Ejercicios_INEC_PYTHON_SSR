from pathlib import Path
from unittest.mock import Mock

from config import Settings
from database import NexusRepository
from services.identity_service import IdentityService


class FakeResponse:
    status_code = 200
    text = "{}"

    def json(self):
        return {
            "driverId": "D-1001",
            "profile": {"fullName": "ana martinez"},
            "compliance": {
                "licenseStatus": "ACTIVE",
                "verified": True,
                "riskScore": 0.08,
            },
            "updatedAt": "2026-07-21T18:30:00Z",
        }


def test_identity_service_maps_provider_payload():
    session = Mock()
    session.request.return_value = FakeResponse()
    service = IdentityService("https://provider.test", Settings(), session=session)

    driver = service.verify_driver("D-1001")

    assert driver.driver_id == "D-1001"
    assert driver.full_name == "Ana Martinez"
    assert driver.verified is True


def test_repository_upserts_driver_without_duplicates(tmp_path):
    db_path = tmp_path / "test.db"
    repo = NexusRepository(str(db_path))
    repo.initialize_schema()

    session = Mock()
    session.request.return_value = FakeResponse()
    service = IdentityService("https://provider.test", Settings(), session=session)
    driver = service.verify_driver("D-1001")

    repo.save_driver(driver)
    repo.save_driver(driver)

    assert repo.count_rows("drivers") == 1
    assert Path(db_path).exists()
    repo.close()
