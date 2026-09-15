"""give every greenhouse an organization

Revision ID: c7d3e1f2a9b4
Revises: bd874695bd2d
Create Date: 2026-09-15 12:10:00.000000

Every greenhouse belongs to exactly one organization
(docs/design/authentication_authorization_plan.md, "Greenhouse ownership").
Greenhouses that exist before this migration are demo, simulator and
research greenhouses no customer owns, so they are moved to the SerraPulse
internal organization, which this migration creates.
"""

from datetime import UTC, datetime
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c7d3e1f2a9b4"
down_revision: str | Sequence[str] | None = "bd874695bd2d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Duplicated from application.auth.models on purpose: a migration must keep
# meaning what it meant when it ran, even if the constants move later.
INTERNAL_ORGANIZATION_ID = "org_serrapulse_internal"
INTERNAL_ORGANIZATION_NAME = "SerraPulse Internal"
INTERNAL_ORGANIZATION_SLUG = "serrapulse-internal"

organizations = sa.table(
    "organizations",
    sa.column("organization_id", sa.String),
    sa.column("name", sa.String),
    sa.column("slug", sa.String),
    sa.column("created_at", sa.String),
)
greenhouses = sa.table(
    "greenhouses",
    sa.column("organization_id", sa.String),
)


def upgrade() -> None:
    """Upgrade schema."""
    connection = op.get_bind()
    exists = connection.execute(
        sa.select(organizations.c.organization_id).where(
            organizations.c.organization_id == INTERNAL_ORGANIZATION_ID
        )
    ).first()
    if exists is None:
        connection.execute(
            organizations.insert().values(
                organization_id=INTERNAL_ORGANIZATION_ID,
                name=INTERNAL_ORGANIZATION_NAME,
                slug=INTERNAL_ORGANIZATION_SLUG,
                created_at=datetime.now(UTC).isoformat(),
            )
        )

    op.add_column("greenhouses", sa.Column("organization_id", sa.String(), nullable=True))
    connection.execute(
        greenhouses.update()
        .where(greenhouses.c.organization_id.is_(None))
        .values(organization_id=INTERNAL_ORGANIZATION_ID)
    )
    with op.batch_alter_table("greenhouses") as batch_op:
        batch_op.alter_column("organization_id", existing_type=sa.String(), nullable=False)
        batch_op.create_foreign_key(
            "fk_greenhouses_organization_id_organizations",
            "organizations",
            ["organization_id"],
            ["organization_id"],
        )
        batch_op.create_index(
            op.f("ix_greenhouses_organization_id"), ["organization_id"], unique=False
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("greenhouses") as batch_op:
        batch_op.drop_index(op.f("ix_greenhouses_organization_id"))
        batch_op.drop_constraint("fk_greenhouses_organization_id_organizations", type_="foreignkey")
        batch_op.drop_column("organization_id")
    op.get_bind().execute(
        organizations.delete().where(organizations.c.organization_id == INTERNAL_ORGANIZATION_ID)
    )
