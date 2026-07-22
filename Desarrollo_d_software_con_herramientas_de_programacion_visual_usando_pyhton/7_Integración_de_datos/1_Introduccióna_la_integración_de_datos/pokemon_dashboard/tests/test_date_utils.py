from datetime import datetime, timezone

import pytest

from utils.date_utils import parse_iso_datetime


def test_parse_iso_datetime_converts_zulu_string_to_utc_datetime() -> None:
    result = parse_iso_datetime("2026-07-10T18:30:45.123Z")

    assert isinstance(result, datetime)
    assert result.tzinfo == timezone.utc
    assert result.year == 2026
    assert result.month == 7
    assert result.day == 10
    assert result.microsecond == 123000


def test_parse_iso_datetime_rejects_invalid_value() -> None:
    with pytest.raises(ValueError, match="Fecha ISO 8601 inválida"):
        parse_iso_datetime("10/07/2026")
