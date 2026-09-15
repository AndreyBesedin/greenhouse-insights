from sqlalchemy import Engine, select
from sqlalchemy.engine import RowMapping

from application.auth.models import Organization
from application.persistence.schema import organizations
from application.persistence.timestamps import from_db_timestamp, to_db_timestamp
from application.persistence.upsert import upsert


class OrganizationRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def save(self, organization: Organization) -> None:
        row = {
            "organization_id": organization.organization_id,
            "name": organization.name,
            "slug": organization.slug,
            "created_at": to_db_timestamp(organization.created_at),
        }
        with self._engine.begin() as connection:
            upsert(connection, organizations, row, key=("organization_id",))

    def get(self, organization_id: str) -> Organization | None:
        statement = select(organizations).where(organizations.c.organization_id == organization_id)
        with self._engine.connect() as connection:
            row = connection.execute(statement).mappings().one_or_none()
        return None if row is None else _row_to_organization(row)

    def get_by_slug(self, slug: str) -> Organization | None:
        statement = select(organizations).where(organizations.c.slug == slug)
        with self._engine.connect() as connection:
            row = connection.execute(statement).mappings().one_or_none()
        return None if row is None else _row_to_organization(row)

    def list_by_ids(self, organization_ids: list[str]) -> list[Organization]:
        if not organization_ids:
            return []
        statement = select(organizations).where(
            organizations.c.organization_id.in_(organization_ids)
        )
        with self._engine.connect() as connection:
            rows = connection.execute(statement).mappings().all()
        return [_row_to_organization(row) for row in rows]

    def list(self) -> list[Organization]:
        with self._engine.connect() as connection:
            rows = connection.execute(select(organizations)).mappings().all()
        return [_row_to_organization(row) for row in rows]


def _row_to_organization(mapping: RowMapping) -> Organization:
    return Organization(
        organization_id=mapping["organization_id"],
        name=mapping["name"],
        slug=mapping["slug"],
        created_at=from_db_timestamp(mapping["created_at"]),
    )
