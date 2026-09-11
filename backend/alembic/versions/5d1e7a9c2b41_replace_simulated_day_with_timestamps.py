"""replace simulated_day with timestamps on generic records

Revision ID: 5d1e7a9c2b41
Revises: 2429be50267d
Create Date: 2026-09-11 12:00:00.000000

Observations, events, state snapshots and recommendations are generic domain
records; their chronology is now the timestamp alone
(docs/design/wur_real_data_ingestion_replay_plan.md section 9). World
snapshots and management traces stay day-keyed: they are simulation-owned.
"""

from datetime import UTC, datetime, timedelta
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "5d1e7a9c2b41"
down_revision: str | Sequence[str] | None = "2429be50267d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _simulation_clock(connection: sa.Connection) -> dict[str, datetime]:
    """greenhouse_id -> the UTC instant of its simulated day 1."""
    rows = connection.execute(
        sa.text("SELECT greenhouse_id, start_date FROM simulation_definitions")
    ).all()
    return {
        greenhouse_id: datetime.combine(
            datetime.fromisoformat(start_date).date(), datetime.min.time(), tzinfo=UTC
        )
        for greenhouse_id, start_date in rows
    }


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("observations") as batch_op:
        batch_op.drop_index(batch_op.f("ix_observations_simulated_day"))
        batch_op.drop_column("simulated_day")
        batch_op.create_index(batch_op.f("ix_observations_timestamp"), ["timestamp"], unique=False)

    with op.batch_alter_table("events") as batch_op:
        batch_op.drop_index(batch_op.f("ix_events_simulated_day"))
        batch_op.drop_column("simulated_day")
        batch_op.create_index(batch_op.f("ix_events_timestamp"), ["timestamp"], unique=False)

    # Re-key state snapshots on (greenhouse_id, timestamp). The timestamp
    # column already exists and is populated, so the rows survive.
    op.rename_table("greenhouse_state_snapshots", "_greenhouse_state_snapshots_old")
    op.create_table(
        "greenhouse_state_snapshots",
        sa.Column("greenhouse_id", sa.String(), nullable=False),
        sa.Column("timestamp", sa.String(), nullable=False),
        sa.Column("state_json", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("greenhouse_id", "timestamp"),
    )
    op.execute(
        "INSERT INTO greenhouse_state_snapshots (greenhouse_id, timestamp, state_json) "
        "SELECT greenhouse_id, timestamp, state_json FROM _greenhouse_state_snapshots_old"
    )
    op.drop_table("_greenhouse_state_snapshots_old")

    # Recommendations: every existing row was simulation-produced, so its
    # context timestamp is the simulation clock's value for its day.
    op.add_column("recommendations", sa.Column("context_timestamp", sa.String(), nullable=True))
    connection = op.get_bind()
    clock = _simulation_clock(connection)
    rows = connection.execute(
        sa.text("SELECT recommendation_id, greenhouse_id, simulated_day FROM recommendations")
    ).all()
    for recommendation_id, greenhouse_id, simulated_day in rows:
        day_one = clock.get(greenhouse_id)
        if day_one is None:
            continue
        context_timestamp = (day_one + timedelta(days=simulated_day - 1)).isoformat()
        connection.execute(
            sa.text(
                "UPDATE recommendations SET context_timestamp = :ts WHERE recommendation_id = :id"
            ),
            {"ts": context_timestamp, "id": recommendation_id},
        )
    op.execute("DELETE FROM recommendations WHERE context_timestamp IS NULL")

    with op.batch_alter_table("recommendations") as batch_op:
        batch_op.alter_column("context_timestamp", nullable=False)
        batch_op.drop_index(batch_op.f("ix_recommendations_simulated_day"))
        batch_op.drop_column("simulated_day")
        batch_op.create_index(
            batch_op.f("ix_recommendations_context_timestamp"), ["context_timestamp"], unique=False
        )


def downgrade() -> None:
    """Downgrade schema."""
    connection = op.get_bind()
    clock = _simulation_clock(connection)

    op.add_column("recommendations", sa.Column("simulated_day", sa.Integer(), nullable=True))
    rows = connection.execute(
        sa.text("SELECT recommendation_id, greenhouse_id, context_timestamp FROM recommendations")
    ).all()
    for recommendation_id, greenhouse_id, context_timestamp in rows:
        day_one = clock.get(greenhouse_id)
        if day_one is None:
            continue
        day = (datetime.fromisoformat(context_timestamp) - day_one).days + 1
        connection.execute(
            sa.text(
                "UPDATE recommendations SET simulated_day = :day WHERE recommendation_id = :id"
            ),
            {"day": day, "id": recommendation_id},
        )
    op.execute("DELETE FROM recommendations WHERE simulated_day IS NULL")
    with op.batch_alter_table("recommendations") as batch_op:
        batch_op.alter_column("simulated_day", nullable=False)
        batch_op.drop_index(batch_op.f("ix_recommendations_context_timestamp"))
        batch_op.drop_column("context_timestamp")
        batch_op.create_index(
            batch_op.f("ix_recommendations_simulated_day"), ["simulated_day"], unique=False
        )

    op.rename_table("greenhouse_state_snapshots", "_greenhouse_state_snapshots_new")
    op.create_table(
        "greenhouse_state_snapshots",
        sa.Column("greenhouse_id", sa.String(), nullable=False),
        sa.Column("simulated_day", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.String(), nullable=False),
        sa.Column("state_json", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("greenhouse_id", "simulated_day"),
    )
    rows = connection.execute(
        sa.text("SELECT greenhouse_id, timestamp, state_json FROM _greenhouse_state_snapshots_new")
    ).all()
    for greenhouse_id, timestamp, state_json in rows:
        day_one = clock.get(greenhouse_id)
        if day_one is None:
            continue
        day = (datetime.fromisoformat(timestamp) - day_one).days + 1
        connection.execute(
            sa.text(
                "INSERT INTO greenhouse_state_snapshots "
                "(greenhouse_id, simulated_day, timestamp, state_json) "
                "VALUES (:gh, :day, :ts, :state)"
            ),
            {"gh": greenhouse_id, "day": day, "ts": timestamp, "state": state_json},
        )
    op.drop_table("_greenhouse_state_snapshots_new")

    with op.batch_alter_table("events") as batch_op:
        batch_op.drop_index(batch_op.f("ix_events_timestamp"))
        batch_op.add_column(
            sa.Column("simulated_day", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.create_index(
            batch_op.f("ix_events_simulated_day"), ["simulated_day"], unique=False
        )

    with op.batch_alter_table("observations") as batch_op:
        batch_op.drop_index(batch_op.f("ix_observations_timestamp"))
        batch_op.add_column(
            sa.Column("simulated_day", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.create_index(
            batch_op.f("ix_observations_simulated_day"), ["simulated_day"], unique=False
        )
