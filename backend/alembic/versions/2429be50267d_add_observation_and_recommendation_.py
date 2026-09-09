"""add observation and recommendation source provenance

Revision ID: 2429be50267d
Revises: 768f499d556d
Create Date: 2026-09-07 22:36:37.370124

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2429be50267d"
down_revision: str | Sequence[str] | None = "768f499d556d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("observations", sa.Column("source_id", sa.String(), nullable=True))

    # Every recommendation persisted so far was simulation-produced (only
    # ActionExecutorType.SIMULATED_OPERATOR exists), so backfill source_type
    # accordingly and carry the old simulation_id over as source_id before
    # dropping it.
    op.add_column(
        "recommendations",
        sa.Column("source_type", sa.String(), server_default="SIMULATION", nullable=False),
    )
    op.add_column("recommendations", sa.Column("source_id", sa.String(), nullable=True))
    op.execute("UPDATE recommendations SET source_id = simulation_id")

    op.drop_index(op.f("ix_recommendations_simulation_id"), table_name="recommendations")
    op.create_index(
        op.f("ix_recommendations_source_id"), "recommendations", ["source_id"], unique=False
    )
    op.drop_column("recommendations", "simulation_id")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column("recommendations", sa.Column("simulation_id", sa.VARCHAR(), nullable=True))
    op.execute("UPDATE recommendations SET simulation_id = source_id")
    with op.batch_alter_table("recommendations") as batch_op:
        batch_op.alter_column("simulation_id", nullable=False)

    op.drop_index(op.f("ix_recommendations_source_id"), table_name="recommendations")
    op.create_index(
        op.f("ix_recommendations_simulation_id"), "recommendations", ["simulation_id"], unique=False
    )
    op.drop_column("recommendations", "source_id")
    op.drop_column("recommendations", "source_type")
    op.drop_column("observations", "source_id")
