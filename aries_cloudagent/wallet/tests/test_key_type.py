from unittest import TestCase

from ...core.error import BaseError
from ..did_method import KEY, SOV, DIDMethods
from ..key_type import BLS12381G2, ED25519

SOV_DID_METHOD_NAME = "sov"
SOV_SUPPORTED_KEY_TYPES = [ED25519]
KEY_DID_METHOD_NAME = "key"


class TestDidMethod(TestCase):
    """TestCases for did method"""

    did_methods = DIDMethods()

    def test_from_metadata(self):
        """Testing 'from_metadata'"""
        assert self.did_methods.from_metadata({"method": SOV_DID_METHOD_NAME}) == SOV
        assert self.did_methods.from_metadata({"method": KEY_DID_METHOD_NAME}) == KEY

        # test backwards compat
        assert self.did_methods.from_metadata({}) == SOV

    def test_from_method(self):
        """Testing 'from_method'"""
        assert self.did_methods.from_method(SOV_DID_METHOD_NAME) == SOV
        assert self.did_methods.from_method(KEY_DID_METHOD_NAME) == KEY
        assert self.did_methods.from_method("random") is None

    def test_from_did(self):
        """Testing 'from_did'"""
        assert self.did_methods.from_did(f"did:{SOV_DID_METHOD_NAME}:xxxx") == SOV
        assert self.did_methods.from_did(f"did:{KEY_DID_METHOD_NAME}:xxxx") == KEY

        with self.assertRaises(BaseError) as context:
            self.did_methods.from_did("did:unknown:something")
        assert "Unsupported did method: unknown" in str(context.exception)

    def test_properties(self):
        """Testing 'properties'"""
        method = SOV

        assert method.method_name == SOV_DID_METHOD_NAME
        assert method.supported_key_types == SOV_SUPPORTED_KEY_TYPES
        assert method.supports_rotation is True

        assert method.supports_key_type(ED25519) == True
        assert method.supports_key_type(BLS12381G2) == False
