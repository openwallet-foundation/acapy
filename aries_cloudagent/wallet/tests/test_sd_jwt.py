from unittest import TestCase
import pytest
from aries_cloudagent.resolver.did_resolver import DIDResolver
from aries_cloudagent.resolver.tests.test_did_resolver import MockResolver
from aries_cloudagent.wallet.default_verification_key_strategy import (
    BaseVerificationKeyStrategy,
    DefaultVerificationKeyStrategy,
)
from jsonpath_ng.ext import parse
import json


from ...core.in_memory.profile import InMemoryProfile
from ...wallet.did_method import KEY, DIDMethods
from ...wallet.key_type import ED25519
from ...wallet.in_memory import InMemoryWallet

from ..jwt import jwt_sign, jwt_verify, resolve_public_key_by_kid_for_verify
from ..sd_jwt import sd_jwt_sign, sd_jwt_verify

from .test_jwt import profile, in_memory_wallet


class TestSDJWT:
    """Tests for JWT sign and verify using dids."""

    seed = "testseed000000000000000000000001"

    @pytest.mark.asyncio
    async def test_sign_with_did_key_and_verify(self, profile, in_memory_wallet):
        did_info = await in_memory_wallet.create_local_did(KEY, ED25519, self.seed)
        did = did_info.did
        verification_method = None
        sd_list = [
            "address",
            "address.street_address",
            "address.street_address.house_number",
            "address.locality",
            "address.region",
            "address.country",
            "given_name",
            "family_name",
            "email",
            "phone_number",
            "phone_number_verified",
            "birthdate",
            "updated_at",
            "nationalities[1:3]",
        ]
        headers = {}
        payload = {
            "sub": "user_42",
            "given_name": "John",
            "family_name": "Doe",
            "email": "johndoe@example.com",
            "phone_number": "+1-202-555-0101",
            "phone_number_verified": True,
            "address": {
                "street_address": {
                    "house_number": "123",
                    "street": "Main St",
                },
                "locality": "Anytown",
                "region": "Anystate",
                "country": "US",
            },
            "birthdate": "1940-01-01",
            "updated_at": 1570000000,
            "nationalities": ["US", "DE", "SA"],
        }
        signed = await sd_jwt_sign(
            profile, headers, payload, sd_list, did, verification_method
        )

        assert signed

        assert await sd_jwt_verify(profile, signed)
