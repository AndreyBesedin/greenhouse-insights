from sqlalchemy import Engine, delete, select
from sqlalchemy.engine import RowMapping

from application.auth.models import OrganizationMembership, OrganizationRole
from application.persistence.schema import organization_memberships
from application.persistence.timestamps import from_db_timestamp, to_db_timestamp
from application.persistence.upsert import upsert


class MembershipRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def save(self, membership: OrganizationMembership) -> None:
        row = {
            "user_id": membership.user_id,
            "organization_id": membership.organization_id,
            "role": membership.role.value,
            "created_at": to_db_timestamp(membership.created_at),
        }
        with self._engine.begin() as connection:
            upsert(
                connection,
                organization_memberships,
                row,
                key=("user_id", "organization_id"),
            )

    def get(self, user_id: str, organization_id: str) -> OrganizationMembership | None:
        statement = select(organization_memberships).where(
            organization_memberships.c.user_id == user_id,
            organization_memberships.c.organization_id == organization_id,
        )
        with self._engine.connect() as connection:
            row = connection.execute(statement).mappings().one_or_none()
        return None if row is None else _row_to_membership(row)

    def list_for_user(self, user_id: str) -> list[OrganizationMembership]:
        statement = select(organization_memberships).where(
            organization_memberships.c.user_id == user_id
        )
        with self._engine.connect() as connection:
            rows = connection.execute(statement).mappings().all()
        return [_row_to_membership(row) for row in rows]

    def list_for_organization(self, organization_id: str) -> list[OrganizationMembership]:
        statement = select(organization_memberships).where(
            organization_memberships.c.organization_id == organization_id
        )
        with self._engine.connect() as connection:
            rows = connection.execute(statement).mappings().all()
        return [_row_to_membership(row) for row in rows]

    def delete(self, user_id: str, organization_id: str) -> None:
        statement = delete(organization_memberships).where(
            organization_memberships.c.user_id == user_id,
            organization_memberships.c.organization_id == organization_id,
        )
        with self._engine.begin() as connection:
            connection.execute(statement)


def _row_to_membership(mapping: RowMapping) -> OrganizationMembership:
    return OrganizationMembership(
        user_id=mapping["user_id"],
        organization_id=mapping["organization_id"],
        role=OrganizationRole(mapping["role"]),
        created_at=from_db_timestamp(mapping["created_at"]),
    )
