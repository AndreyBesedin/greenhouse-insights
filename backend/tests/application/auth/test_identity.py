import pytest
from sqlalchemy import Engine

from application.auth.identity import (
    AuthenticatedIdentity,
    DevHeaderAuthenticator,
    NotAuthenticated,
    UserResolver,
    actor_for,
)
from application.persistence.user_repository import UserRepository

IDENTITY = AuthenticatedIdentity(
    auth_subject="auth0|abc123", email="grower@acme.example", display_name="A. Grower"
)


def test_dev_header_authenticator_reads_the_subject_header() -> None:
    identity = DevHeaderAuthenticator().authenticate({"x-dev-subject": " dev-alice "})

    assert identity.auth_subject == "dev-alice"
    assert identity.email == "dev-alice@dev.local"


def test_dev_header_authenticator_rejects_a_missing_or_blank_header() -> None:
    with pytest.raises(NotAuthenticated):
        DevHeaderAuthenticator().authenticate({})
    with pytest.raises(NotAuthenticated):
        DevHeaderAuthenticator().authenticate({"x-dev-subject": "  "})


def test_resolver_creates_the_user_on_first_sight_and_reuses_it_after(engine: Engine) -> None:
    resolver = UserResolver(engine, platform_admin_subjects=frozenset())

    first = resolver.resolve(IDENTITY)
    second = resolver.resolve(IDENTITY)

    assert first == second
    assert first.email == "grower@acme.example"
    assert first.is_platform_admin is False
    assert len(UserRepository(engine).list()) == 1


def test_resolver_keys_identity_by_subject_not_email(engine: Engine) -> None:
    resolver = UserResolver(engine, platform_admin_subjects=frozenset())
    original = resolver.resolve(IDENTITY)

    same_email_other_subject = resolver.resolve(
        AuthenticatedIdentity(auth_subject="auth0|zzz", email="grower@acme.example")
    )

    assert same_email_other_subject.user_id != original.user_id
    assert len(UserRepository(engine).list()) == 2


def test_resolver_grants_platform_admin_to_bootstrap_subjects(engine: Engine) -> None:
    resolver = UserResolver(engine, platform_admin_subjects=frozenset({"auth0|abc123"}))

    user = resolver.resolve(IDENTITY)

    assert user.is_platform_admin is True
    stored = UserRepository(engine).get(user.user_id)
    assert stored is not None and stored.is_platform_admin is True


def test_removing_a_subject_from_the_bootstrap_list_does_not_revoke(engine: Engine) -> None:
    """Revocation is an explicit operation, never a side effect of config."""
    UserResolver(engine, platform_admin_subjects=frozenset({"auth0|abc123"})).resolve(IDENTITY)

    user = UserResolver(engine, platform_admin_subjects=frozenset()).resolve(IDENTITY)

    assert user.is_platform_admin is True


def test_actor_for_carries_the_user_id_and_platform_admin_flag(engine: Engine) -> None:
    user = UserResolver(engine, platform_admin_subjects=frozenset({"auth0|abc123"})).resolve(
        IDENTITY
    )

    actor = actor_for(user)

    assert actor.actor_id == user.user_id
    assert actor.is_platform_admin is True
