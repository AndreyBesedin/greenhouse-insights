"""Bearer-token authentication against a provider we stand in for with a
locally generated signing key: valid tokens become identities, and every
way a token can be wrong is refused."""

import time
from collections.abc import Mapping
from typing import Any

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from application.auth.identity import NotAuthenticated
from application.auth.oidc import OidcAuthenticator, OidcSettings

ISSUER = "https://serrapulse-test.eu.auth0.com/"
AUDIENCE = "https://api.serrapulse.test"
SETTINGS = OidcSettings(issuer=ISSUER, audience=AUDIENCE)

KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


class StaticKeys:
    def __init__(self, keys: dict[str, rsa.RSAPrivateKey]) -> None:
        self._keys = keys

    def signing_key(self, token: str) -> Any:
        kid = jwt.get_unverified_header(token).get("kid")
        if kid not in self._keys:
            raise jwt.PyJWKClientError(f"unknown kid {kid!r}")
        return self._keys[kid].public_key()


class FakeUserInfo:
    def __init__(self, profile: Mapping[str, Any] | Exception) -> None:
        self.profile = profile
        self.calls = 0

    def fetch(self, token: str) -> Mapping[str, Any]:
        self.calls += 1
        if isinstance(self.profile, Exception):
            raise self.profile
        return self.profile


def token(
    *,
    key: rsa.RSAPrivateKey = KEY,
    kid: str = "k1",
    sub: str = "auth0|abc",
    issuer: str = ISSUER,
    audience: str | list[str] = AUDIENCE,
    expires_in: int = 3600,
    algorithm: str = "RS256",
    **extra: Any,
) -> str:
    now = int(time.time())
    claims = {"iss": issuer, "aud": audience, "sub": sub, "iat": now, "exp": now + expires_in}
    claims.update(extra)
    return jwt.encode(claims, key, algorithm=algorithm, headers={"kid": kid})


def bearer(value: str) -> dict[str, str]:
    return {"authorization": f"Bearer {value}"}


@pytest.fixture
def authenticator() -> OidcAuthenticator:
    return OidcAuthenticator(SETTINGS, StaticKeys({"k1": KEY}))


def test_a_valid_token_with_email_claim_becomes_an_identity(
    authenticator: OidcAuthenticator,
) -> None:
    identity = authenticator.authenticate(
        bearer(token(email="grower@acme.example", name="A. Grower"))
    )

    assert identity.auth_subject == "auth0|abc"
    assert identity.email == "grower@acme.example"
    assert identity.display_name == "A. Grower"


def test_custom_claim_names_are_honoured() -> None:
    settings = OidcSettings(
        issuer=ISSUER,
        audience=AUDIENCE,
        email_claim="https://serrapulse/email",
        name_claim="https://serrapulse/name",
    )
    authenticator = OidcAuthenticator(settings, StaticKeys({"k1": KEY}))
    claims: dict[str, Any] = {
        "https://serrapulse/email": "x@acme.example",
        "https://serrapulse/name": "X",
    }

    identity = authenticator.authenticate(bearer(token(**claims)))

    assert (identity.email, identity.display_name) == ("x@acme.example", "X")


def test_an_audience_list_containing_ours_is_accepted(authenticator: OidcAuthenticator) -> None:
    identity = authenticator.authenticate(
        bearer(token(audience=[AUDIENCE, f"{ISSUER}userinfo"], email="a@b.c"))
    )

    assert identity.auth_subject == "auth0|abc"


@pytest.mark.parametrize(
    ("bad", "reason"),
    [
        ({"key": OTHER_KEY}, "signed by a key the provider does not publish"),
        ({"kid": "unknown"}, "unknown key id"),
        ({"issuer": "https://someone-else.example/"}, "wrong issuer"),
        ({"audience": "https://other-api"}, "wrong audience"),
        ({"expires_in": -60}, "expired"),
    ],
)
def test_bad_tokens_are_refused(
    authenticator: OidcAuthenticator, bad: dict[str, Any], reason: str
) -> None:
    with pytest.raises(NotAuthenticated):
        authenticator.authenticate(bearer(token(email="a@b.c", **bad)))


def test_symmetric_tokens_are_refused_even_with_a_matching_secret() -> None:
    """alg confusion: an HS256 token must never be accepted."""
    authenticator = OidcAuthenticator(SETTINGS, StaticKeys({"k1": KEY}))
    now = int(time.time())
    forged = jwt.encode(
        {"iss": ISSUER, "aud": AUDIENCE, "sub": "x", "iat": now, "exp": now + 60, "email": "a@b"},
        "not-a-secret-but-long-enough-for-hmac-sha256!",
        algorithm="HS256",
        headers={"kid": "k1"},
    )

    with pytest.raises(NotAuthenticated):
        authenticator.authenticate(bearer(forged))


def test_missing_or_malformed_authorization_is_refused(
    authenticator: OidcAuthenticator,
) -> None:
    with pytest.raises(NotAuthenticated):
        authenticator.authenticate({})
    with pytest.raises(NotAuthenticated):
        authenticator.authenticate({"authorization": "Basic abc"})
    with pytest.raises(NotAuthenticated):
        authenticator.authenticate({"authorization": "Bearer "})
    with pytest.raises(NotAuthenticated):
        authenticator.authenticate(bearer("not.a.jwt"))


def test_a_token_without_email_fetches_userinfo_once_per_subject() -> None:
    userinfo = FakeUserInfo({"email": "grower@acme.example", "name": "Via Userinfo"})
    clock = [1000.0]
    authenticator = OidcAuthenticator(
        SETTINGS, StaticKeys({"k1": KEY}), userinfo, clock=lambda: clock[0]
    )

    first = authenticator.authenticate(bearer(token()))
    second = authenticator.authenticate(bearer(token()))
    clock[0] += 16 * 60
    third = authenticator.authenticate(bearer(token()))

    assert first.email == second.email == third.email == "grower@acme.example"
    assert first.display_name == "Via Userinfo"
    assert userinfo.calls == 2  # cached for fifteen minutes, then refreshed


def test_a_token_without_email_and_no_userinfo_is_refused(
    authenticator: OidcAuthenticator,
) -> None:
    with pytest.raises(NotAuthenticated):
        authenticator.authenticate(bearer(token()))


def test_userinfo_failures_are_refused_not_crashed() -> None:
    failing = OidcAuthenticator(
        SETTINGS, StaticKeys({"k1": KEY}), FakeUserInfo(httpx.ConnectError("down"))
    )
    with pytest.raises(NotAuthenticated):
        failing.authenticate(bearer(token()))

    no_email = OidcAuthenticator(SETTINGS, StaticKeys({"k1": KEY}), FakeUserInfo({"name": "X"}))
    with pytest.raises(NotAuthenticated):
        no_email.authenticate(bearer(token()))


def test_settings_derive_provider_urls_from_the_issuer() -> None:
    assert SETTINGS.jwks_url == f"{ISSUER}.well-known/jwks.json"
    assert SETTINGS.userinfo_url == f"{ISSUER}userinfo"
