"""Test json-ld credential."""

import asyncio
import json
import pytest

from itertools import cycle

from asynctest import mock as async_mock, TestCase as AsyncTestCase

from ....admin.request_context import AdminRequestContext
from ....core.in_memory import InMemoryProfile
from ....vc.ld_proofs import DocumentLoader
from ....wallet.base import BaseWallet
from ....wallet.in_memory import InMemoryWallet
from ....wallet.key_type import ED25519

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
from .document_loader import custom_document_loader


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


class TestOps(AsyncTestCase):
    async def setUp(self):
        self.wallet = InMemoryWallet(InMemoryProfile.test_profile())
        await self.wallet.create_signing_key(ED25519, TEST_SEED)

        self.session = InMemoryProfile.test_session(bind={BaseWallet: self.wallet})
        self.profile = self.session.profile
        self.context = self.profile.context
        setattr(
            self.profile,
            "session",
            async_mock.MagicMock(return_value=self.session),
        )

        self.context.injector.bind_instance(DocumentLoader, custom_document_loader)

    async def test_verify_credential(self):
        for input_ in TEST_VERIFY_OBJS:
            assert await verify_credential(
                self.session,
                input_.get("doc"),
                input_.get("verkey"),
            )

    async def test_sign_credential(self):
        for input_ in TEST_SIGN_OBJS:
            result = await sign_credential(
                self.session,
                input_.get("doc"),
                input_.get("options"),
                TEST_VERKEY,
            )
            assert "proof" in result.keys()
            assert "jws" in result.get("proof", {}).keys()

    async def test_sign_dropped_attribute_exception(self):
        for input_ in TEST_SIGN_ERROR_OBJS:
            with self.assertRaises(DroppedAttributeError) as context:
                await sign_credential(
                    self.session,
                    input_.get("doc"),
                    input_.get("options"),
                    TEST_VERKEY,
                )
            assert "attribute2drop" in str(context.exception)

    async def test_signature_option_type(self):
        for input_ in TEST_SIGN_OBJS:
            with self.assertRaises(SignatureTypeError):
                input_["options"]["type"] = "Ed25519Signature2038"
                await sign_credential(
                    self.session,
                    input_.get("doc"),
                    input_.get("options"),
                    TEST_VERKEY,
                )

    async def test_invalid_jws_header(self):
        with self.assertRaises(BadJWSHeaderError):
            await verify_credential(
                self.session,
                TEST_VERIFY_ERROR.get("doc"),
                TEST_VERIFY_ERROR.get("verkey"),
            )

    async def test_did_key(self):
        for verkey in (
            "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx",
            "did:key:z3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx",
        ):
            assert did_key(verkey).startswith("did:key:z")
