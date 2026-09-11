"""WUR timestamps arrive in Dutch local time - the 2024 CSVs with an explicit
offset (+02:00 / +01:00 across the DST change), the 2023 workbooks as Excel
serial dates with none. Everything becomes a timezone-aware UTC datetime
here, so downstream ordering and "<= T" comparisons are exact."""

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

WUR_LOCAL_TIMEZONE = ZoneInfo("Europe/Amsterdam")

_EXCEL_EPOCH = datetime(1899, 12, 30)


def parse_offset_timestamp(value: str) -> datetime:
    """'2024-09-03 00:05:00+02:00' -> aware UTC datetime."""
    parsed = datetime.fromisoformat(value.strip())
    if parsed.tzinfo is None:
        raise ValueError(f"WUR timestamp {value!r} has no UTC offset")
    return parsed.astimezone(UTC)


def local_noon(day: date) -> datetime:
    """A manual measurement whose source gives only a date: pinned to local
    noon so it sorts inside that day's readings rather than at midnight."""
    return datetime.combine(day, time(12, 0), tzinfo=WUR_LOCAL_TIMEZONE).astimezone(UTC)


def excel_serial_to_utc(serial: float) -> datetime:
    """Excel serial day number in Dutch local time -> aware UTC datetime,
    rounded to the nearest second (serials carry float noise)."""
    naive = _EXCEL_EPOCH + timedelta(days=serial)
    naive = (naive + timedelta(microseconds=500_000)).replace(microsecond=0)
    return naive.replace(tzinfo=WUR_LOCAL_TIMEZONE).astimezone(UTC)
