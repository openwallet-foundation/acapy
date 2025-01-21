from typing import Tuple
from unittest import IsolatedAsyncioTestCase

import pytest

from ...resolver.did_resolver import DIDResolver
from ...resolver.tests.test_did_resolver import MockResolver
from ...utils.testing import create_test_profile
from ...wallet.did_method import KEY, DIDMethods
from ...wallet.key_type import ED25519, P256, KeyType, KeyTypes
from ..base import BaseWallet
from ..default_verification_key_strategy import (
    BaseVerificationKeyStrategy,
    DefaultVerificationKeyStrategy,
)
from ..jwt import jwt_sign, jwt_verify, resolve_public_key_by_kid_for_verify


class TestJWT(IsolatedAsyncioTestCase):
    """Tests for JWT sign and verify using dids."""

    seed = "testseed000000000000000000000001"
    did_key_ed25519_did = "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"
    did_key_ed25519_verification_method = "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"
    did_key_ed25519_doc = {
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
    }
    did_key_p256_did = "did:key:zDnaehWviigWQQD7bqF3btFquwA5w8DX2sQwkVxnAyJ7oxdjq"
    did_key_p256_verification_method = "did:key:zDnaehWviigWQQD7bqF3btFquwA5w8DX2sQwkVxnAyJ7oxdjq#zDnaehWviigWQQD7bqF3btFquwA5w8DX2sQwkVxnAyJ7oxdjq"
    did_key_p256_doc = {
        "@context": [
            "https://www.w3.org/ns/did/v1",
            "https://w3id.org/security/multikey/v1",
        ],
        "id": "did:key:zDnaehWviigWQQD7bqF3btFquwA5w8DX2sQwkVxnAyJ7oxdjq",
        "verificationMethod": [
            {
                "id": "did:key:zDnaehWviigWQQD7bqF3btFquwA5w8DX2sQwkVxnAyJ7oxdjq#zDnaehWviigWQQD7bqF3btFquwA5w8DX2sQwkVxnAyJ7oxdjq",
                "type": "Multikey",
                "controller": "did:key:zDnaehWviigWQQD7bqF3btFquwA5w8DX2sQwkVxnAyJ7oxdjq",
                "publicKeyMultibase": "zDnaehWviigWQQD7bqF3btFquwA5w8DX2sQwkVxnAyJ7oxdjq",
            }
        ],
        "authentication": [
            "did:key:zDnaehWviigWQQD7bqF3btFquwA5w8DX2sQwkVxnAyJ7oxdjq#zDnaehWviigWQQD7bqF3btFquwA5w8DX2sQwkVxnAyJ7oxdjq"
        ],
        "assertionMethod": [
            "did:key:zDnaehWviigWQQD7bqF3btFquwA5w8DX2sQwkVxnAyJ7oxdjq#zDnaehWviigWQQD7bqF3btFquwA5w8DX2sQwkVxnAyJ7oxdjq"
        ],
        "capabilityDelegation": [
            "did:key:zDnaehWviigWQQD7bqF3btFquwA5w8DX2sQwkVxnAyJ7oxdjq#zDnaehWviigWQQD7bqF3btFquwA5w8DX2sQwkVxnAyJ7oxdjq"
        ],
        "capabilityInvocation": [
            "did:key:zDnaehWviigWQQD7bqF3btFquwA5w8DX2sQwkVxnAyJ7oxdjq#zDnaehWviigWQQD7bqF3btFquwA5w8DX2sQwkVxnAyJ7oxdjq"
        ],
        "keyAgreement": [],
    }

    async def asyncSetUp(self):
        self.profile = await create_test_profile()
        self.profile.context.injector.bind_instance(DIDMethods, DIDMethods())
        self.profile.context.injector.bind_instance(
            BaseVerificationKeyStrategy, DefaultVerificationKeyStrategy()
        )
        self.profile.context.injector.bind_instance(KeyTypes, KeyTypes())

    async def setUpTestingDid(self, key_type: KeyType) -> Tuple[str, str]:
        async with self.profile.session() as session:
            wallet = session.inject(BaseWallet)
            await wallet.create_local_did(KEY, key_type, self.seed)

        if key_type == P256:
            did = self.did_key_p256_did
            vm_id = self.did_key_p256_verification_method
            did_doc = self.did_key_p256_doc
        elif key_type == ED25519:
            did = self.did_key_ed25519_did
            vm_id = self.did_key_ed25519_verification_method
            did_doc = self.did_key_ed25519_doc

        resolver = DIDResolver()
        resolver.register_resolver(
            MockResolver(
                ["key"],
                resolved=did_doc,
                native=True,
            )
        )
        self.profile.context.injector.bind_instance(DIDResolver, resolver)

        return (did, vm_id)

    async def test_sign_with_did_key_and_verify(self):
        for key_type in [ED25519, P256]:
            (did, _) = await self.setUpTestingDid(key_type)
            verification_method = None

            headers = {}
            payload = {}
            signed = await jwt_sign(
                self.profile, headers, payload, did, verification_method
            )

            assert signed

            assert await jwt_verify(self.profile, signed)

    async def test_sign_with_verification_method_and_verify(self):
        for key_type in [ED25519, P256]:
            (_, verification_method) = await self.setUpTestingDid(key_type)
            did = None
            headers = {}
            payload = {}
            signed: str = await jwt_sign(
                self.profile, headers, payload, did, verification_method
            )

            assert signed

            assert await jwt_verify(self.profile, signed)

    async def test_sign_x_invalid_did(self):
        did = "did:key:zzzzgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"
        headers = {}
        payload = {}
        verification_method = None
        with pytest.raises(Exception) as e_info:
            await jwt_sign(self.profile, headers, payload, did, verification_method)
        assert "No key type for prefixed public key" in str(e_info)

    async def test_sign_x_invalid_verification_method(self):
        did = None
        headers = {}
        payload = {}
        verification_method = "did:key:zzzzgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"
        with pytest.raises(Exception) as e_info:
            await jwt_sign(self.profile, headers, payload, did, verification_method)
        assert "Unknown DID" in str(e_info)

    async def test_verify_x_invalid_signed(self):
        for key_type in [ED25519, P256]:
            (did, _) = await self.setUpTestingDid(key_type)
            verification_method = None

            headers = {}
            payload = {}
            signed = await jwt_sign(
                self.profile, headers, payload, did, verification_method
            )

            assert signed
            signed = f"{signed[:-2]}2"

            with pytest.raises(Exception):
                await jwt_verify(self.profile, signed)

    async def test_resolve_public_key_by_kid_for_verify_ed25519(self):
        (_, kid) = await self.setUpTestingDid(ED25519)
        (key_bs58, key_type) = await resolve_public_key_by_kid_for_verify(
            self.profile, kid
        )

        assert key_bs58 == "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
        assert key_type == ED25519

    async def test_resolve_public_key_by_kid_for_verify_p256(self):
        (_, kid) = await self.setUpTestingDid(P256)
        (key_bs58, key_type) = await resolve_public_key_by_kid_for_verify(
            self.profile, kid
        )

        assert key_bs58 == "tYbR5egjfja9D5ix1jjYGqfh5QPu73RcZ7UjQUXtargj"
        assert key_type == P256
