"""Test json-ld credential."""

import asyncio
import json
import pytest

from itertools import cycle

from asynctest import mock as async_mock, TestCase as AsyncTestCase

from ....admin.request_context import AdminRequestContext
from ....core.in_memory import InMemoryProfile
from ....vc.tests.document_loader import custom_document_loader
from ....wallet.base import BaseWallet
from ....wallet.in_memory import InMemoryWallet
from ....wallet.key_type import KeyType

from .. import credential as test_module
from ..create_verify_data import DroppedAttributeError
from ..credential import did_key, sign_credential, verify_credential
from ..error import BadJWSHeaderError, SignatureTypeError

from . import (
    TEST_SEED,
    TEST_SIGN_ERROR_OBJS,
    TEST_SIGN_OBJS,
    TEST_VALIDATE_ERROR_OBJ2,
    TEST_VERIFY_ERROR,
    TEST_VERIFY_OBJS,
    TEST_VERKEY,
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
    await wallet.create_signing_key(KeyType.ED25519, TEST_SEED)
    yield wallet


@pytest.fixture(scope="module")
async def mock_session(wallet):
    session_inject = {BaseWallet: wallet}
    context = AdminRequestContext.test_context(session_inject)
    session = await context.session()
    yield session


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

    '''
    @pytest.mark.parametrize("input_", TEST_VERIFY_OBJS)
    async def test_verify_credential(self, input_, mock_session):
        result = await verify_credential(
            mock_session, input_.get("doc"), input_.get("verkey")
        )
        assert result

    @pytest.mark.parametrize("input_", TEST_SIGN_OBJS)
    async def test_sign_credential(self, input_, mock_session):
        result = await sign_credential(
            mock_session, input_.get("doc"), input_.get("options"), TEST_VERKEY
        )
        assert "proof" in result.keys()
        assert "jws" in result.get("proof", {}).keys()

    @pytest.mark.parametrize("input_", TEST_SIGN_ERROR_OBJS)
    async def test_sign_dropped_attribute_exception(self, input_, mock_session):
        with pytest.raises(DroppedAttributeError, match="attribute2drop"):
            await sign_credential(
                mock_session, input_.get("doc"), input_.get("options"), TEST_VERKEY
            )

    async def test_validate_dropped_attribute_exception(self, mock_session):
        with pytest.raises(DroppedAttributeError, match="attribute2drop"):
            input_ = TEST_VALIDATE_ERROR_OBJ2
            await verify_credential(
                mock_session, input_["doc"], TEST_VERIFY_ERROR["verkey"]
            )

    @pytest.mark.parametrize("input_", TEST_SIGN_OBJS)
    async def test_signature_option_type(self, input_, mock_session):
        with pytest.raises(SignatureTypeError):
            input_["options"]["type"] = "Ed25519Signature2038"
            await sign_credential(
                mock_session, input_.get("doc"), input_.get("options"), TEST_VERKEY
            )

    @pytest.mark.parametrize("input_", TEST_VERIFY_OBJS)
    async def test_verify_option_type(self, input_, mock_session):
        with pytest.raises(SignatureTypeError):
            input_["doc"]["proof"]["type"] = "Ed25519Signature2038"
            await verify_credential(
                mock_session, input_.get("doc"), input_.get("verkey")
            )
    '''

    async def test_invalid_JWS_header(self, mock_session):
        with pytest.raises(BadJWSHeaderError):
            await verify_credential(
                mock_session,
                TEST_VERIFY_ERROR.get("doc"),
                TEST_VERIFY_ERROR.get("verkey"),
            )

    '''
    @pytest.mark.parametrize(
        "verkey",
        (
            "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx",
            "did:key:z3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx",
        ),
    )
    async def test_did_key(self, verkey):
        assert did_key(verkey).startswith("did:key:z")
    '''
