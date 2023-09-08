import pytest
from aries_cloudagent.resolver.did_resolver import DIDResolver
from aries_cloudagent.resolver.tests.test_did_resolver import MockResolver
from aries_cloudagent.wallet.default_verification_key_strategy import (
    BaseVerificationKeyStrategy,
    DefaultVerificationKeyStrategy,
)

from ...core.in_memory.profile import InMemoryProfile
from ...wallet.did_method import DIDMethods
from ...wallet.in_memory import InMemoryWallet


@pytest.fixture()
async def profile():
    """In memory profile with injected dependencies."""

    mock_sov = MockResolver(
        ["key"],
        resolved={
            "@context": "https://www.w3.org/ns/did/v1",
            "id": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
            "verificationMethod": [
                {
                    "id": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
                    "type": "Ed25519VerificationKey2018",
                    "controller": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
                    "publicKeyBase58": "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx",
                }
            ],
            "authentication": [
                "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"
            ],
            "assertionMethod": [
                "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"
            ],
            "capabilityDelegation": [
                "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"
            ],
            "capabilityInvocation": [
                "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"
            ],
            "keyAgreement": [
                {
                    "id": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6LSbkodSr6SU2trs8VUgnrnWtSm7BAPG245ggrBmSrxbv1R",
                    "type": "X25519KeyAgreementKey2019",
                    "controller": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
                    "publicKeyBase58": "5dTvYHaNaB7mk7iA9LqCJEHG2dGZQsvoi8WGzDRtYEf",
                }
            ],
        },
        native=True,
    )
    yield InMemoryProfile.test_profile(
        bind={
            DIDMethods: DIDMethods(),
            BaseVerificationKeyStrategy: DefaultVerificationKeyStrategy(),
            DIDResolver: DIDResolver([mock_sov]),
        }
    )


@pytest.fixture()
async def in_memory_wallet(profile):
    """In memory wallet for testing."""
    yield InMemoryWallet(profile)
