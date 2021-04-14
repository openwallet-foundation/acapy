"""Test json-ld credential."""

import json
from asynctest import mock as async_mock, TestCase as AsyncTestCase
import pytest
import asyncio
from .. import credential as test_module
from itertools import cycle
from ....admin.request_context import AdminRequestContext
from ..credential import (
    verify_credential,
    sign_credential,
    did_key,
)
from ..error import SignatureTypeError, BadJWSHeaderError
from ..create_verify_data import DroppedAttributeError
from ....core.in_memory import InMemoryProfile
from ....wallet.in_memory import InMemoryWallet
from ....wallet.base import BaseWallet
from . import (
    TEST_SEED,
    TEST_VERKEY,
    TEST_VERIFY_OBJS,
    TEST_SIGN_OBJS,
    TEST_SIGN_ERROR_OBJS,
    TEST_VALIDATE_ERROR_OBJ2,
    TEST_VERIFY_ERROR,
)


class TestCredential(AsyncTestCase):
    async def test_did_key(self):
        did_key = test_module.did_key(TEST_VERKEY)
        assert did_key.startswith("did:key:z")
        assert did_key == test_module.did_key(did_key)

    async def test_verify_jws_header(self):
        test_module.verify_jws_header(
            json.loads(
                test_module.b64decode(
                    "eyJhbGciOiJFZERTQSIsImI2NCI6ZmFsc2UsImNyaXQiOlsiYjY0Il19"
                )
            )
        )

        with self.assertRaises(test_module.BadJWSHeaderError):
            test_module.verify_jws_header(
                json.loads(
                    test_module.b64decode(  # {... "b64": True ...}
                        "eyJhbGciOiJFZERTQSIsImI2NCI6dHJ1ZSwiY3JpdCI6WyJiNjQiXX0="
                    )
                )
            )


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def wallet():
    profile = InMemoryProfile.test_profile()
    wallet = InMemoryWallet(profile)
    await wallet.create_signing_key(TEST_SEED)
    yield wallet


@pytest.fixture(scope="module")
async def mock_session(wallet):
    session_inject = {BaseWallet: wallet}
    context = AdminRequestContext.test_context(session_inject)
    session = await context.session()
    yield session


@pytest.mark.parametrize("input", TEST_VERIFY_OBJS)
@pytest.mark.asyncio
async def test_verify_credential(input, mock_session):
    result = await verify_credential(
        mock_session, input.get("doc"), input.get("verkey")
    )
    assert result


@pytest.mark.parametrize("input", TEST_SIGN_OBJS)
@pytest.mark.asyncio
async def test_sign_credential(input, mock_session):
    result = await sign_credential(
        mock_session, input.get("doc"), input.get("options"), TEST_VERKEY
    )
    assert "proof" in result.keys()
    assert "jws" in result.get("proof", {}).keys()


@pytest.mark.parametrize("input", TEST_SIGN_ERROR_OBJS)
@pytest.mark.asyncio
async def test_sign_dropped_attribute_exception(input, mock_session):
    with pytest.raises(DroppedAttributeError, match="attribute2drop"):
        await sign_credential(
            mock_session, input.get("doc"), input.get("options"), TEST_VERKEY
        )


@pytest.mark.asyncio
async def test_validate_dropped_attribute_exception(mock_session):
    with pytest.raises(DroppedAttributeError, match="attribute2drop"):
        input = TEST_VALIDATE_ERROR_OBJ2
        await verify_credential(mock_session, input["doc"], TEST_VERIFY_ERROR["verkey"])


@pytest.mark.parametrize("input", TEST_SIGN_OBJS)
@pytest.mark.asyncio
async def test_signature_option_type(input, mock_session):
    with pytest.raises(SignatureTypeError):
        input["options"]["type"] = "Ed25519Signature2038"
        await sign_credential(
            mock_session, input.get("doc"), input.get("options"), TEST_VERKEY
        )


@pytest.mark.parametrize("input", TEST_VERIFY_OBJS)
@pytest.mark.asyncio
async def test_verify_optiion_type(input, mock_session):
    with pytest.raises(SignatureTypeError):
        input["doc"]["proof"]["type"] = "Ed25519Signature2038"
        await verify_credential(mock_session, input.get("doc"), input.get("verkey"))


@pytest.mark.asyncio
async def test_Invalid_JWS_header(mock_session):
    with pytest.raises(BadJWSHeaderError):
        await verify_credential(
            mock_session, TEST_VERIFY_ERROR.get("doc"), TEST_VERIFY_ERROR.get("verkey")
        )


@pytest.mark.parametrize(
    "verkey",
    (
        "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx",
        "did:key:z3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx",
    ),
)
def test_did_key(verkey):
    assert did_key(verkey).startswith("did:key:z")
