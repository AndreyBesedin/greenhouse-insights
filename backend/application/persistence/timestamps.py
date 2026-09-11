"""One canonical on-disk form for every domain timestamp.

Timestamps are stored as ISO-8601 strings and compared lexically in SQL
(`timestamp <= :at`), which is only correct if every stored value uses the
same offset. Recorded datasets arrive in local time (WUR: CET/CEST with
explicit offsets), the simulator emits UTC - so everything is normalised
to UTC on the way in and returned timezone-aware on the way out.
"""

from datetime import UTC, datetime


def to_db_timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError(f"timestamp {value.isoformat()} must be timezone-aware")
    return value.astimezone(UTC).isoformat()


def from_db_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value)
