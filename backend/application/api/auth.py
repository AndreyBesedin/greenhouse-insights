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
from application.auth.oidc import (
    HttpUserInfoSource,
    JwksKeySource,
    OidcAuthenticator,
    OidcSettings,
)

AUTH_MODE_ENV_VAR = "GREENHOUSE_AUTH_MODE"
PLATFORM_ADMIN_SUBJECTS_ENV_VAR = "GREENHOUSE_PLATFORM_ADMIN_SUBJECTS"
OIDC_ISSUER_ENV_VAR = "GREENHOUSE_OIDC_ISSUER"
OIDC_AUDIENCE_ENV_VAR = "GREENHOUSE_OIDC_AUDIENCE"
OIDC_EMAIL_CLAIM_ENV_VAR = "GREENHOUSE_OIDC_EMAIL_CLAIM"
OIDC_NAME_CLAIM_ENV_VAR = "GREENHOUSE_OIDC_NAME_CLAIM"


class AuthMode(StrEnum):
    # Trust an X-Dev-Subject header. Local development and tests only.
    DEV = "dev"
    # Validate bearer tokens from an OpenID Connect provider (Auth0).
    OIDC = "oidc"


@dataclass(frozen=True)
class AuthSettings:
    mode: AuthMode
    platform_admin_subjects: frozenset[str]
    oidc: OidcSettings | None = None

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
        oidc = _oidc_settings_from_env() if mode == AuthMode.OIDC else None
        return cls(
            mode=mode,
            platform_admin_subjects=frozenset(s.strip() for s in subjects.split(",") if s.strip()),
            oidc=oidc,
        )

    def authenticator(self) -> Authenticator:
        """Builds the authenticator for this mode. Build it once per
        process: the OIDC one caches the provider's signing keys."""
        if self.mode == AuthMode.DEV:
            return DevHeaderAuthenticator()
        if self.mode == AuthMode.OIDC:
            assert self.oidc is not None
            return OidcAuthenticator(
                self.oidc,
                JwksKeySource(self.oidc.jwks_url),
                HttpUserInfoSource(self.oidc.userinfo_url),
            )
        raise AssertionError(f"unhandled auth mode {self.mode}")


def _oidc_settings_from_env() -> OidcSettings:
    issuer = os.environ.get(OIDC_ISSUER_ENV_VAR, "").strip()
    audience = os.environ.get(OIDC_AUDIENCE_ENV_VAR, "").strip()
    missing = [
        name
        for name, value in ((OIDC_ISSUER_ENV_VAR, issuer), (OIDC_AUDIENCE_ENV_VAR, audience))
        if not value
    ]
    if missing:
        raise RuntimeError(f"{AUTH_MODE_ENV_VAR}=oidc requires {', '.join(missing)}")
    if not issuer.startswith("https://"):
        raise RuntimeError(f"{OIDC_ISSUER_ENV_VAR} must be an https:// URL")
    return OidcSettings(
        issuer=issuer,
        audience=audience,
        email_claim=os.environ.get(OIDC_EMAIL_CLAIM_ENV_VAR, "email").strip() or "email",
        name_claim=os.environ.get(OIDC_NAME_CLAIM_ENV_VAR, "name").strip() or "name",
    )


def get_auth_settings(request: Request) -> AuthSettings:
    settings: AuthSettings = request.app.state.auth_settings
    return settings


def get_authenticator(request: Request) -> Authenticator:
    """The process-wide authenticator built at startup from the settings
    (see AuthSettings.authenticator)."""
    authenticator: Authenticator = request.app.state.authenticator
    return authenticator


def get_actor(
    request: Request,
    engine: Engine = Depends(get_engine),
    settings: AuthSettings = Depends(get_auth_settings),
    authenticator: Authenticator = Depends(get_authenticator),
) -> ActorContext:
    identity = authenticator.authenticate(request.headers)
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
