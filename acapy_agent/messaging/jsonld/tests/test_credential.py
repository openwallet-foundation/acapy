"""Test json-ld credential."""

import json
from unittest import IsolatedAsyncioTestCase

from ....utils.testing import create_test_profile, skip_on_jsonld_url_error
from ....wallet.base import BaseWallet
from ....wallet.key_type import ED25519
from .. import credential as test_module
from ..create_verify_data import DroppedAttributeError
from ..credential import did_key, sign_credential, verify_credential
from ..error import BadJWSHeaderError, SignatureTypeError
from . import (
    TEST_SEED,
    TEST_SIGN_ERROR_OBJS,
    TEST_SIGN_OBJS,
    TEST_VERIFY_ERROR,
    TEST_VERIFY_OBJS,
    TEST_VERKEY,
)


class TestCredential(IsolatedAsyncioTestCase):
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


class TestOps(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.profile = await create_test_profile()
        async with self.profile.session() as session:
            self.wallet = session.inject(BaseWallet)
            await self.wallet.create_signing_key(ED25519, TEST_SEED)

    @skip_on_jsonld_url_error
    async def test_verify_credential(self):
        async with self.profile.session() as session:
            for input_ in TEST_VERIFY_OBJS:
                assert await verify_credential(
                    session,
                    input_.get("doc"),
                    input_.get("verkey"),
                )

    async def test_sign_credential(self):
        async with self.profile.session() as session:
            for input_ in TEST_SIGN_OBJS:
                result = await sign_credential(
                    session,
                    input_.get("doc"),
                    input_.get("options"),
                    TEST_VERKEY,
                )
                assert "proof" in result.keys()
                assert "jws" in result.get("proof", {}).keys()

    @skip_on_jsonld_url_error
    async def test_sign_dropped_attribute_exception(self):
        async with self.profile.session() as session:
            for input_ in TEST_SIGN_ERROR_OBJS:
                with self.assertRaises(DroppedAttributeError) as context:
                    await sign_credential(
                        session,
                        input_.get("doc"),
                        input_.get("options"),
                        TEST_VERKEY,
                    )
                assert "attribute2drop" in str(context.exception)

    async def test_signature_option_type(self):
        async with self.profile.session() as session:
            for input_ in TEST_SIGN_OBJS:
                with self.assertRaises(SignatureTypeError):
                    input_["options"]["type"] = "Ed25519Signature2038"
                    await sign_credential(
                        session,
                        input_.get("doc"),
                        input_.get("options"),
                        TEST_VERKEY,
                    )

    @skip_on_jsonld_url_error
    async def test_invalid_jws_header(self):
        with self.assertRaises(BadJWSHeaderError):
            async with self.profile.session() as session:
                await verify_credential(
                    session,
                    TEST_VERIFY_ERROR.get("doc"),
                    TEST_VERIFY_ERROR.get("verkey"),
                )

    async def test_did_key(self):
        for verkey in (
            "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx",
            "did:key:z3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx",
        ):
            assert did_key(verkey).startswith("did:key:z")
