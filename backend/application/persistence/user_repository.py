from sqlalchemy import Engine, select
from sqlalchemy.engine import RowMapping

from application.auth.models import User
from application.persistence.schema import users
from application.persistence.timestamps import from_db_timestamp, to_db_timestamp
from application.persistence.upsert import upsert


class UserRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def save(self, user: User) -> None:
        row = {
            "user_id": user.user_id,
            "auth_subject": user.auth_subject,
            "email": user.email,
            "display_name": user.display_name,
            "is_platform_admin": user.is_platform_admin,
            "created_at": to_db_timestamp(user.created_at),
        }
        with self._engine.begin() as connection:
            upsert(connection, users, row, key=("user_id",))

    def get(self, user_id: str) -> User | None:
        statement = select(users).where(users.c.user_id == user_id)
        with self._engine.connect() as connection:
            row = connection.execute(statement).mappings().one_or_none()
        return None if row is None else _row_to_user(row)

    def get_by_auth_subject(self, auth_subject: str) -> User | None:
        statement = select(users).where(users.c.auth_subject == auth_subject)
        with self._engine.connect() as connection:
            row = connection.execute(statement).mappings().one_or_none()
        return None if row is None else _row_to_user(row)

    def list(self) -> list[User]:
        with self._engine.connect() as connection:
            rows = connection.execute(select(users)).mappings().all()
        return [_row_to_user(row) for row in rows]


def _row_to_user(mapping: RowMapping) -> User:
    return User(
        user_id=mapping["user_id"],
        auth_subject=mapping["auth_subject"],
        email=mapping["email"],
        display_name=mapping["display_name"],
        is_platform_admin=bool(mapping["is_platform_admin"]),
        created_at=from_db_timestamp(mapping["created_at"]),
    )
