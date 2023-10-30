import pytest

from aries_cloudagent.wallet.did_method import DIDMethods, DIDMethod, HolderDefinedDid
from aries_cloudagent.wallet.did_parameters_validation import DIDParametersValidation
from aries_cloudagent.wallet.error import WalletError
from aries_cloudagent.wallet.key_type import ED25519, BLS12381G1


@pytest.fixture
def did_methods_registry():
    return DIDMethods()


def test_validate_key_type_uses_didmethod_when_validating_key_type(
    did_methods_registry,
):
    # given
    ed_method = DIDMethod("ed-method", [ED25519])
    did_methods_registry.register(ed_method)
    did_validation = DIDParametersValidation(did_methods_registry)

    # when - then
    assert did_validation.validate_key_type(ed_method, ED25519) is None
    with pytest.raises(WalletError):
        did_validation.validate_key_type(ed_method, BLS12381G1)


def test_validate_key_type_raises_exception_when_validating_unknown_did_method(
    did_methods_registry,
):
    # given
    unknown_method = DIDMethod("unknown", [])
    did_validation = DIDParametersValidation(did_methods_registry)

    # when - then
    with pytest.raises(WalletError):
        did_validation.validate_key_type(unknown_method, ED25519)


def test_set_did_raises_error_when_did_is_provided_and_method_doesnt_allow(
    did_methods_registry,
):
    # given
    ed_method = DIDMethod(
        "derived-did", [ED25519], holder_defined_did=HolderDefinedDid.NO
    )
    did_methods_registry.register(ed_method)
    did_validation = DIDParametersValidation(did_methods_registry)

    # when - then
    with pytest.raises(WalletError):
        did_validation.validate_or_derive_did(
            ed_method, ED25519, b"verkey", "did:edward:self-defined"
        )


def test_validate_or_derive_did_raises_error_when_no_did_is_provided_and_method_requires_one(
    did_methods_registry,
):
    # given
    ed_method = DIDMethod(
        "self-defined-did", [ED25519], holder_defined_did=HolderDefinedDid.REQUIRED
    )
    did_methods_registry.register(ed_method)
    did_validation = DIDParametersValidation(did_methods_registry)

    # when - then
    with pytest.raises(WalletError):
        did_validation.validate_or_derive_did(ed_method, ED25519, b"verkey", did=None)


def test_validate_or_derive_did_raises_exception_when_validating_unknown_did_method(
    did_methods_registry,
):
    # given
    unknown_method = DIDMethod("unknown", [])
    did_validation = DIDParametersValidation(did_methods_registry)

    # when - then
    with pytest.raises(WalletError):
        did_validation.validate_or_derive_did(
            unknown_method, ED25519, b"verkey", did=None
        )
