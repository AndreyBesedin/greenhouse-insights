"""HTTP authentication: validate the credential, resolve the local user,
hand routes an ActorContext. This is where a request becomes an actor;
it is not where authorization happens - the application services
authorize each operation themselves, so calling them from a CLI or a
worker enforces exactly the same rules
(docs/design/authentication_authorization_plan.md, "HTTP/API behavior").
"""

import os
from dataclasses import dataclass
from enum import StrEnum

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import Engine

from application.api.dependencies import get_engine
from application.auth.actor import ActorContext
from application.auth.authorizer import Forbidden
from application.auth.identity import (
    Authenticator,
    DevHeaderAuthenticator,
    NotAuthenticated,
    UserResolver,
    actor_for,
)

AUTH_MODE_ENV_VAR = "GREENHOUSE_AUTH_MODE"
PLATFORM_ADMIN_SUBJECTS_ENV_VAR = "GREENHOUSE_PLATFORM_ADMIN_SUBJECTS"


class AuthMode(StrEnum):
    # Trust an X-Dev-Subject header. Local development and tests only.
    DEV = "dev"


@dataclass(frozen=True)
class AuthSettings:
    mode: AuthMode
    platform_admin_subjects: frozenset[str]

    @classmethod
    def from_env(cls) -> "AuthSettings":
        """No default mode on purpose: a deployment that forgot to
        configure authentication must fail to start, not run open."""
        raw_mode = os.environ.get(AUTH_MODE_ENV_VAR)
        if not raw_mode:
            raise RuntimeError(
                f"{AUTH_MODE_ENV_VAR} is not set; use {AuthMode.DEV.value!r} for local development"
            )
        try:
            mode = AuthMode(raw_mode.strip().lower())
        except ValueError as exc:
            raise RuntimeError(
                f"{AUTH_MODE_ENV_VAR}={raw_mode!r} is not one of {[m.value for m in AuthMode]}"
            ) from exc
        subjects = os.environ.get(PLATFORM_ADMIN_SUBJECTS_ENV_VAR, "")
        return cls(
            mode=mode,
            platform_admin_subjects=frozenset(s.strip() for s in subjects.split(",") if s.strip()),
        )

    def authenticator(self) -> Authenticator:
        if self.mode == AuthMode.DEV:
            return DevHeaderAuthenticator()
        raise AssertionError(f"unhandled auth mode {self.mode}")


def get_auth_settings(request: Request) -> AuthSettings:
    settings: AuthSettings = request.app.state.auth_settings
    return settings


def get_actor(
    request: Request,
    engine: Engine = Depends(get_engine),
    settings: AuthSettings = Depends(get_auth_settings),
) -> ActorContext:
    identity = settings.authenticator().authenticate(request.headers)
    resolver = UserResolver(engine, platform_admin_subjects=settings.platform_admin_subjects)
    return actor_for(resolver.resolve(identity))


def install_auth_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotAuthenticated)
    def _not_authenticated(request: Request, exc: NotAuthenticated) -> JSONResponse:
        return JSONResponse(
            status_code=401,
            content={"detail": "not authenticated"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(Forbidden)
    def _forbidden(request: Request, exc: Forbidden) -> JSONResponse:
        return JSONResponse(status_code=403, content={"detail": "forbidden"})
