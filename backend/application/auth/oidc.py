"""The identity-provider mode: bearer access tokens issued by an OpenID
Connect provider (Auth0 initially), validated locally against the
provider's published signing keys. Nothing here is Auth0-specific beyond
the defaults: any provider that issues RS256 JWTs with an issuer, an
audience and a subject fits
(docs/design/authentication_authorization_plan.md, "Identity provider
boundary").
"""

import logging
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx
import jwt

from application.auth.identity import AuthenticatedIdentity, NotAuthenticated

logger = logging.getLogger(__name__)

ALGORITHMS = ["RS256"]
USERINFO_CACHE_SECONDS = 15 * 60


@dataclass(frozen=True)
class OidcSettings:
    # e.g. https://your-tenant.eu.auth0.com/ - must match the token's iss
    # exactly, trailing slash included.
    issuer: str
    # The API identifier the token must be issued for (aud).
    audience: str
    # Where the claims come from. Access tokens for a custom API usually
    # carry only the subject; the provider adds email/name either as
    # (namespaced) custom claims or through the userinfo endpoint.
    email_claim: str = "email"
    name_claim: str = "name"

    @property
    def jwks_url(self) -> str:
        return self.issuer.rstrip("/") + "/.well-known/jwks.json"

    @property
    def userinfo_url(self) -> str:
        return self.issuer.rstrip("/") + "/userinfo"


class KeySource(Protocol):
    def signing_key(self, token: str) -> Any:
        """The public key that signed `token`, or raises jwt exceptions."""
        ...


class JwksKeySource:
    """Fetches and caches the provider's signing keys."""

    def __init__(self, jwks_url: str) -> None:
        self._client = jwt.PyJWKClient(jwks_url, cache_keys=True)

    def signing_key(self, token: str) -> Any:
        return self._client.get_signing_key_from_jwt(token).key


class UserInfoSource(Protocol):
    def fetch(self, token: str) -> Mapping[str, Any]: ...


class HttpUserInfoSource:
    def __init__(self, userinfo_url: str) -> None:
        self._url = userinfo_url

    def fetch(self, token: str) -> Mapping[str, Any]:
        response = httpx.get(self._url, headers={"Authorization": f"Bearer {token}"}, timeout=10.0)
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        return data


@dataclass
class _CachedProfile:
    email: str
    name: str | None
    expires_at: float = field(default=0.0)


class OidcAuthenticator:
    def __init__(
        self,
        settings: OidcSettings,
        keys: KeySource,
        userinfo: UserInfoSource | None = None,
        *,
        clock: Any = time.monotonic,
    ) -> None:
        self._settings = settings
        self._keys = keys
        self._userinfo = userinfo
        self._clock = clock
        # Profiles fetched from userinfo, by subject, so a token that
        # carries no email claim does not cost one provider call per
        # request.
        self._profiles: dict[str, _CachedProfile] = {}

    def authenticate(self, headers: Mapping[str, str]) -> AuthenticatedIdentity:
        token = _bearer_token(headers)
        try:
            key = self._keys.signing_key(token)
            claims = jwt.decode(
                token,
                key,
                algorithms=ALGORITHMS,
                audience=self._settings.audience,
                issuer=self._settings.issuer,
                options={"require": ["exp", "iat", "sub"]},
            )
        except jwt.PyJWTError as exc:
            raise NotAuthenticated(f"invalid token: {exc}") from exc

        subject = str(claims["sub"])
        email = claims.get(self._settings.email_claim)
        name = claims.get(self._settings.name_claim)
        if not email:
            profile = self._profile(subject, token)
            email, name = profile.email, name or profile.name
        return AuthenticatedIdentity(auth_subject=subject, email=email, display_name=name)

    def _profile(self, subject: str, token: str) -> _CachedProfile:
        cached = self._profiles.get(subject)
        now = self._clock()
        if cached is not None and cached.expires_at > now:
            return cached
        if self._userinfo is None:
            raise NotAuthenticated(
                f"token for {subject!r} carries no {self._settings.email_claim!r} claim "
                "and no userinfo endpoint is configured"
            )
        try:
            info = self._userinfo.fetch(token)
        except httpx.HTTPError as exc:
            raise NotAuthenticated(f"could not fetch userinfo: {exc}") from exc
        email = info.get("email")
        if not email:
            raise NotAuthenticated(f"identity provider supplied no email for {subject!r}")
        profile = _CachedProfile(
            email=str(email),
            name=info.get("name"),
            expires_at=now + USERINFO_CACHE_SECONDS,
        )
        self._profiles[subject] = profile
        return profile


def _bearer_token(headers: Mapping[str, str]) -> str:
    authorization = headers.get("authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise NotAuthenticated("missing bearer token")
    return token.strip()
