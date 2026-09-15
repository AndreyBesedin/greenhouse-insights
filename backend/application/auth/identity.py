"""Authentication: turning a credential into a local User.

An Authenticator proves who is calling from whatever the transport
carried (a bearer token, a development header) and returns the identity
provider's view of them; the UserResolver then maps that to the local
User row by the provider's stable subject, creating the row on first
sight. Nothing past this module sees provider-specific objects
(docs/design/authentication_authorization_plan.md, "Identity provider
boundary").
"""

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import uuid4

from sqlalchemy import Engine

from application.auth.actor import ActorContext
from application.auth.audit import AuditAction, AuditEvent
from application.auth.models import User
from application.persistence.audit_repository import AuditRepository
from application.persistence.user_repository import UserRepository

logger = logging.getLogger(__name__)

DEV_SUBJECT_HEADER = "x-dev-subject"
# The audit actor when the platform acts from configuration, not a user.
BOOTSTRAP_ACTOR_ID = "system:bootstrap"
PLATFORM_ADMIN_BOOTSTRAP_SOURCE = "GREENHOUSE_PLATFORM_ADMIN_SUBJECTS"


class NotAuthenticated(Exception):
    """No usable credential came with the request."""


@dataclass(frozen=True)
class AuthenticatedIdentity:
    """What the credential proved, in provider-neutral terms."""

    auth_subject: str
    email: str
    display_name: str | None = None


class Authenticator(Protocol):
    def authenticate(self, headers: Mapping[str, str]) -> AuthenticatedIdentity:
        """Returns the identity behind `headers` (names lower-cased) or
        raises NotAuthenticated."""
        ...


class DevHeaderAuthenticator:
    """Development only: the caller says who they are in a header. Any
    subject is accepted, so this must never be the configured mode
    anywhere reachable from the internet - main.py only enables it when
    GREENHOUSE_AUTH_MODE is explicitly "dev"."""

    def authenticate(self, headers: Mapping[str, str]) -> AuthenticatedIdentity:
        subject = headers.get(DEV_SUBJECT_HEADER, "").strip()
        if not subject:
            raise NotAuthenticated(f"missing {DEV_SUBJECT_HEADER} header")
        return AuthenticatedIdentity(
            auth_subject=subject, email=f"{subject}@dev.local", display_name=subject
        )


class UserResolver:
    """Maps an authenticated identity to the local User, creating it on
    first login. `platform_admin_subjects` is the deployment's bootstrap
    list: those subjects are granted platform admin when they log in (the
    grant is logged; revoking is a separate, explicit operation, never a
    side effect of editing configuration)."""

    def __init__(self, engine: Engine, *, platform_admin_subjects: frozenset[str]) -> None:
        self._users = UserRepository(engine)
        self._audit = AuditRepository(engine)
        self._platform_admin_subjects = platform_admin_subjects

    def resolve(self, identity: AuthenticatedIdentity) -> User:
        user = self._users.get_by_auth_subject(identity.auth_subject)
        if user is None:
            user = User(
                user_id=f"user_{uuid4().hex[:12]}",
                auth_subject=identity.auth_subject,
                email=identity.email,
                display_name=identity.display_name,
                created_at=datetime.now(UTC),
            )
            self._users.save(user)
            logger.info("created user %s for subject %s", user.user_id, identity.auth_subject)
        if identity.auth_subject in self._platform_admin_subjects and not user.is_platform_admin:
            user = user.model_copy(update={"is_platform_admin": True})
            self._users.save(user)
            logger.warning(
                "granted platform admin to user %s (subject %s) from the bootstrap list",
                user.user_id,
                identity.auth_subject,
            )
            self._audit.append(
                AuditEvent(
                    audit_id=f"aud_{uuid4().hex[:12]}",
                    timestamp=datetime.now(UTC),
                    actor_id=BOOTSTRAP_ACTOR_ID,
                    action=AuditAction.PLATFORM_ADMIN_GRANTED,
                    target_type="user",
                    target_id=user.user_id,
                    details={"email": user.email, "source": PLATFORM_ADMIN_BOOTSTRAP_SOURCE},
                )
            )
        return user


def actor_for(user: User) -> ActorContext:
    return ActorContext.user(user.user_id, is_platform_admin=user.is_platform_admin)
