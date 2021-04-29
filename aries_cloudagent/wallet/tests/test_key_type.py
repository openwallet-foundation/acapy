from unittest import TestCase

from ...core.error import BaseError
from ..did_method import DIDMethod
from ..key_type import KeyType

SOV_DID_METHOD_NAME = "sov"
SOV_SUPPORTED_KEY_TYPES = [KeyType.ED25519]
KEY_DID_METHOD_NAME = "key"


class TestDidMethod(TestCase):
    def test_from_metadata(self):
        assert DIDMethod.from_metadata({"method": SOV_DID_METHOD_NAME}) == DIDMethod.SOV
        assert DIDMethod.from_metadata({"method": KEY_DID_METHOD_NAME}) == DIDMethod.KEY

        # test backwards compat
        assert DIDMethod.from_metadata({}) == DIDMethod.SOV

    def test_from_method(self):
        assert DIDMethod.from_method(SOV_DID_METHOD_NAME) == DIDMethod.SOV
        assert DIDMethod.from_method(KEY_DID_METHOD_NAME) == DIDMethod.KEY
        assert DIDMethod.from_method("random") == None

    def test_from_did(self):
        assert DIDMethod.from_did(f"did:{SOV_DID_METHOD_NAME}:xxxx") == DIDMethod.SOV
        assert DIDMethod.from_did(f"did:{KEY_DID_METHOD_NAME}:xxxx") == DIDMethod.KEY

        with self.assertRaises(BaseError) as context:
            DIDMethod.from_did("did:unknown:something")
        assert "Unsupported did method: unknown" in str(context.exception)

    def test_properties(self):
        method = DIDMethod.SOV

        assert method.method_name == SOV_DID_METHOD_NAME
        assert method.supported_key_types == SOV_SUPPORTED_KEY_TYPES
        assert method.supports_rotation == True

        assert method.supports_key_type(KeyType.ED25519) == True
        assert method.supports_key_type(KeyType.BLS12381G2) == False
