"""Tests for the OAuth2 token validator."""

import asyncio
import time
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase

import aiohttp
import jwt
from aiohttp import web
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from ...tests import mock
from ..oauth_validator import OAuthTokenValidator

ISSUER = "https://as.example.com/realms/test"
AUDIENCE = "acapy-admin"
JWKS_URI = "https://as.example.com/realms/test/protocol/openid-connect/certs"
INTROSPECTION_ENDPOINT = (
    "https://as.example.com/realms/test/protocol/openid-connect/token/introspect"
)

RSA_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
RSA_PRIVATE_PEM = RSA_KEY.private_bytes(
    serialization.Encoding.PEM,
    serialization.PrivateFormat.PKCS8,
    serialization.NoEncryption(),
)
RSA_PUBLIC_KEY = RSA_KEY.public_key()

OTHER_RSA_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER_RSA_PRIVATE_PEM = OTHER_RSA_KEY.private_bytes(
    serialization.Encoding.PEM,
    serialization.PrivateFormat.PKCS8,
    serialization.NoEncryption(),
)


def make_jwt(
    *,
    key=RSA_PRIVATE_PEM,
    algorithm="RS256",
    exp_delta=300,
    issuer=ISSUER,
    audience=AUDIENCE,
    sub="user-123",
    drop_claims=(),
    **extra_claims,
) -> str:
    claims = {
        "exp": int(time.time()) + exp_delta,
        "iss": issuer,
        "aud": audience,
        "sub": sub,
        **extra_claims,
    }
    for claim in drop_claims:
        claims.pop(claim, None)
    return jwt.encode(claims, key, algorithm=algorithm)


def make_validator(**settings) -> OAuthTokenValidator:
    return OAuthTokenValidator(settings)


def make_jwks_validator(**settings) -> OAuthTokenValidator:
    """Validator with JWKS configured and key lookup returning the test key."""
    validator = make_validator(
        **{
            "oauth.jwks_uri": JWKS_URI,
            "oauth.issuer": ISSUER,
            "oauth.audience": AUDIENCE,
            **settings,
        }
    )
    validator._jwks_client.get_signing_key_from_jwt = mock.MagicMock(
        return_value=SimpleNamespace(key=RSA_PUBLIC_KEY)
    )
    return validator


def make_response(status=200, body=None):
    response = mock.MagicMock(status=status)
    response.json = mock.CoroutineMock(return_value=body or {})
    return response


def mock_session(response=None, post_exc=None):
    """Mock ClientSession whose post() context manager yields response."""
    post_cm = mock.MagicMock()
    if post_exc:
        post_cm.__aenter__ = mock.CoroutineMock(side_effect=post_exc)
    else:
        post_cm.__aenter__ = mock.CoroutineMock(return_value=response)
    post_cm.__aexit__ = mock.CoroutineMock(return_value=False)
    session = mock.MagicMock()
    session.post = mock.MagicMock(return_value=post_cm)
    return session


class TestValidatorConfig(IsolatedAsyncioTestCase):
    def test_jwks_client_only_created_when_configured(self):
        assert make_validator()._jwks_client is None
        assert make_validator(**{"oauth.jwks_uri": JWKS_URI})._jwks_client

    async def test_no_validation_method_raises_unauthorized(self):
        validator = make_validator()
        with self.assertRaises(web.HTTPUnauthorized):
            await validator.validate("any-token")

    def test_http_timeout_default(self):
        validator = make_validator(**{"oauth.jwks_uri": JWKS_URI})
        assert validator.http_timeout == 10
        assert validator._jwks_client.timeout == 10

    async def test_http_timeout_override_applies_to_jwks_and_session(self):
        validator = make_validator(
            **{
                "oauth.jwks_uri": JWKS_URI,
                "oauth.introspection_endpoint": INTROSPECTION_ENDPOINT,
                "oauth.http_timeout": 3,
            }
        )
        assert validator.http_timeout == 3
        assert validator._jwks_client.timeout == 3
        session = validator._get_session()
        assert session.timeout.total == 3
        await validator.close()


class TestJwtValidation(IsolatedAsyncioTestCase):
    async def test_valid_jwt_returns_claims(self):
        validator = make_jwks_validator()
        token = make_jwt(scope="acapy:tenant", wallet_id="wallet-1")
        claims = await validator.validate(token)
        assert claims["sub"] == "user-123"
        assert claims["scope"] == "acapy:tenant"
        assert claims["wallet_id"] == "wallet-1"

    async def test_expired_jwt_rejected(self):
        validator = make_jwks_validator()
        with self.assertRaises(web.HTTPUnauthorized):
            await validator.validate(make_jwt(exp_delta=-300))

    async def test_wrong_issuer_rejected(self):
        validator = make_jwks_validator()
        with self.assertRaises(web.HTTPUnauthorized):
            await validator.validate(make_jwt(issuer="https://evil.example.com"))

    async def test_wrong_audience_rejected(self):
        validator = make_jwks_validator()
        with self.assertRaises(web.HTTPUnauthorized):
            await validator.validate(make_jwt(audience="other-api"))

    async def test_missing_required_claim_rejected(self):
        validator = make_jwks_validator()
        with self.assertRaises(web.HTTPUnauthorized):
            await validator.validate(make_jwt(drop_claims=("sub",)))

    async def test_wrong_signing_key_rejected(self):
        validator = make_jwks_validator()
        with self.assertRaises(web.HTTPUnauthorized):
            await validator.validate(make_jwt(key=OTHER_RSA_PRIVATE_PEM))

    async def test_symmetric_algorithm_rejected(self):
        """HS256 tokens must be rejected (algorithm confusion protection)."""
        validator = make_jwks_validator()
        with self.assertRaises(web.HTTPUnauthorized):
            await validator.validate(make_jwt(key="shared-secret", algorithm="HS256"))

    async def test_issuer_and_audience_not_enforced_when_unset(self):
        validator = make_jwks_validator(**{"oauth.issuer": None, "oauth.audience": None})
        claims = await validator.validate(
            make_jwt(issuer="https://any.example.com", audience="any-api")
        )
        assert claims["sub"] == "user-123"

    async def test_opaque_token_without_introspection_rejected(self):
        validator = make_jwks_validator()
        with self.assertRaises(web.HTTPUnauthorized):
            await validator.validate("not-a-jwt")

    async def test_opaque_token_falls_back_to_introspection(self):
        validator = make_jwks_validator(
            **{"oauth.introspection_endpoint": INTROSPECTION_ENDPOINT}
        )
        validator._introspect = mock.CoroutineMock(
            return_value={"active": True, "sub": "user-123"}
        )
        claims = await validator.validate("not-a-jwt")
        assert claims["sub"] == "user-123"
        validator._introspect.assert_awaited_once_with("not-a-jwt")

    async def test_jwks_error_without_introspection_rejected(self):
        validator = make_jwks_validator()
        validator._jwks_client.get_signing_key_from_jwt = mock.MagicMock(
            side_effect=jwt.exceptions.PyJWKClientError("JWKS fetch failed")
        )
        with self.assertRaises(web.HTTPUnauthorized):
            await validator.validate(make_jwt())

    async def test_jwks_error_falls_back_to_introspection(self):
        validator = make_jwks_validator(
            **{"oauth.introspection_endpoint": INTROSPECTION_ENDPOINT}
        )
        validator._jwks_client.get_signing_key_from_jwt = mock.MagicMock(
            side_effect=jwt.exceptions.PyJWKClientError("JWKS fetch failed")
        )
        validator._introspect = mock.CoroutineMock(return_value={"active": True})
        assert await validator.validate(make_jwt()) == {"active": True}


class TestIntrospection(IsolatedAsyncioTestCase):
    def make_introspection_validator(self, **settings):
        return make_validator(
            **{"oauth.introspection_endpoint": INTROSPECTION_ENDPOINT, **settings}
        )

    async def test_active_token_returns_claims(self):
        validator = self.make_introspection_validator()
        session = mock_session(
            make_response(body={"active": True, "sub": "svc-1", "scope": "acapy:admin"})
        )
        validator._get_session = mock.MagicMock(return_value=session)
        claims = await validator.validate("opaque-token")
        assert claims["sub"] == "svc-1"
        session.post.assert_called_once_with(
            INTROSPECTION_ENDPOINT,
            data={"token": "opaque-token", "token_type_hint": "access_token"},
            auth=None,
        )

    async def test_client_credentials_sent_as_basic_auth(self):
        validator = self.make_introspection_validator(
            **{
                "oauth.introspection_client_id": "acapy-rs",
                "oauth.introspection_client_secret": "s3cret",
            }
        )
        session = mock_session(make_response(body={"active": True}))
        validator._get_session = mock.MagicMock(return_value=session)
        await validator.validate("opaque-token")
        auth = session.post.call_args.kwargs["auth"]
        assert auth == aiohttp.BasicAuth("acapy-rs", "s3cret")

    async def test_inactive_token_rejected(self):
        validator = self.make_introspection_validator()
        validator._get_session = mock.MagicMock(
            return_value=mock_session(make_response(body={"active": False}))
        )
        with self.assertRaises(web.HTTPUnauthorized):
            await validator.validate("opaque-token")

    async def test_non_200_response_rejected(self):
        validator = self.make_introspection_validator()
        validator._get_session = mock.MagicMock(
            return_value=mock_session(make_response(status=503))
        )
        with self.assertRaises(web.HTTPUnauthorized):
            await validator.validate("opaque-token")

    async def test_network_error_returns_service_unavailable(self):
        validator = self.make_introspection_validator()
        validator._get_session = mock.MagicMock(
            return_value=mock_session(
                post_exc=aiohttp.ClientConnectionError("connection refused")
            )
        )
        with self.assertRaises(web.HTTPServiceUnavailable):
            await validator.validate("opaque-token")

    async def test_timeout_returns_service_unavailable(self):
        validator = self.make_introspection_validator()
        validator._get_session = mock.MagicMock(
            return_value=mock_session(post_exc=asyncio.TimeoutError())
        )
        with self.assertRaises(web.HTTPServiceUnavailable):
            await validator.validate("opaque-token")

    async def test_session_reused_and_closed(self):
        validator = self.make_introspection_validator()
        session = validator._get_session()
        assert validator._get_session() is session
        await validator.close()
        assert session.closed
        assert validator._session is None
        # close is idempotent
        await validator.close()
        # a fresh session is created after close
        replacement = validator._get_session()
        assert replacement is not session
        await validator.close()
