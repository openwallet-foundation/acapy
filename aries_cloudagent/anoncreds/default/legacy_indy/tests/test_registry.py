"""Test LegacyIndyRegistry."""

import pytest
import re
from ..registry import LegacyIndyRegistry
from base58 import alphabet

B58 = alphabet if isinstance(alphabet, str) else alphabet.decode("ascii")
INDY_DID = rf"^(did:sov:)?[{B58}]{{21,22}}$"
INDY_SCHEMA_ID = rf"^[{B58}]{{21,22}}:2:.+:[0-9.]+$"
INDY_CRED_DEF_ID = (
    rf"^([{B58}]{{21,22}})"  # issuer DID
    f":3"  # cred def id marker
    f":CL"  # sig alg
    rf":(([1-9][0-9]*)|([{B58}]{{21,22}}:2:.+:[0-9.]+))"  # schema txn / id
    f":(.+)?$"  # tag
)
INDY_REV_REG_DEF_ID = (
    rf"^([{B58}]{{21,22}}):4:"
    rf"([{B58}]{{21,22}}):3:"
    rf"CL:(([1-9][0-9]*)|([{B58}]{{21,22}}:2:.+:[0-9.]+))(:.+)?:"
    rf"CL_ACCUM:(.+$)"
)
SUPPORTED_ID_REGEX = re.compile(
    rf"{INDY_DID}|{INDY_SCHEMA_ID}|{INDY_CRED_DEF_ID}|{INDY_REV_REG_DEF_ID}"
)

TEST_INDY_DID = "WgWxqztrNooG92RXvxSTWv"
TEST_INDY_DID_1 = "did:sov:WgWxqztrNooG92RXvxSTWv"
TEST_INDY_SCHEMA_ID = "WgWxqztrNooG92RXvxSTWv:2:schema_name:1.0"
TEST_INDY_CRED_DEF_ID = "WgWxqztrNooG92RXvxSTWv:3:CL:20:tag"
TEST_INDY_REV_REG_DEF_ID = (
    "WgWxqztrNooG92RXvxSTWv:4:WgWxqztrNooG92RXvxSTWv:3:CL:20:tag:CL_ACCUM:0"
)


@pytest.fixture
def registry():
    """Registry fixture"""
    yield LegacyIndyRegistry()


@pytest.mark.indy
class TestLegacyIndyRegistry:
    @pytest.mark.asyncio
    async def test_supported_did_regex(self, registry: LegacyIndyRegistry):
        """Test the supported_did_regex."""

        assert registry.supported_identifiers_regex == SUPPORTED_ID_REGEX
        assert bool(registry.supported_identifiers_regex.match(TEST_INDY_DID))
        assert bool(registry.supported_identifiers_regex.match(TEST_INDY_DID_1))
        assert bool(registry.supported_identifiers_regex.match(TEST_INDY_SCHEMA_ID))
        assert bool(
            registry.supported_identifiers_regex.match(TEST_INDY_REV_REG_DEF_ID)
        )
