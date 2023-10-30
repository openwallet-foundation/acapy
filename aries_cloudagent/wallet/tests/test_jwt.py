import pytest

from aries_cloudagent.wallet.key_type import ED25519

from ...wallet.did_method import KEY

from ..jwt import jwt_sign, jwt_verify, resolve_public_key_by_kid_for_verify


class TestJWT:
    """Tests for JWT sign and verify using dids."""

    seed = "testseed000000000000000000000001"

    @pytest.mark.asyncio
    async def test_sign_with_did_key_and_verify(self, profile, in_memory_wallet):
        did_info = await in_memory_wallet.create_local_did(KEY, ED25519, self.seed)
        did = did_info.did
        verification_method = None

        headers = {}
        payload = {}
        signed = await jwt_sign(profile, headers, payload, did, verification_method)

        assert signed

        assert await jwt_verify(profile, signed)

    @pytest.mark.asyncio
    async def test_sign_with_verification_method_and_verify(
        self, profile, in_memory_wallet
    ):
        did_info = await in_memory_wallet.create_local_did(KEY, ED25519, self.seed)
        did = None
        verification_method = "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"
        headers = {}
        payload = {}
        signed: str = await jwt_sign(
            profile, headers, payload, did, verification_method
        )

        assert signed

        assert await jwt_verify(profile, signed)

    @pytest.mark.asyncio
    async def test_sign_x_invalid_did(self, profile):
        did = "did:key:zzzzgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"
        headers = {}
        payload = {}
        verification_method = None
        with pytest.raises(Exception) as e_info:
            await jwt_sign(profile, headers, payload, did, verification_method)
        assert "No key type for prefixed public key" in str(e_info)

    @pytest.mark.asyncio
    async def test_sign_x_invalid_verification_method(self, profile):
        did = None
        headers = {}
        payload = {}
        verification_method = "did:key:zzzzgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"
        with pytest.raises(Exception) as e_info:
            await jwt_sign(profile, headers, payload, did, verification_method)
        assert "DID not found:" in str(e_info)

    @pytest.mark.asyncio
    async def test_verify_x_invalid_signed(self, profile, in_memory_wallet):
        did_info = await in_memory_wallet.create_local_did(KEY, ED25519, self.seed)
        did = did_info.did
        verification_method = None

        headers = {}
        payload = {}
        signed = await jwt_sign(profile, headers, payload, did, verification_method)

        assert signed
        signed = f"{signed[:-2]}2"

        with pytest.raises(Exception) as e_info:
            await jwt_verify(profile, signed)

    @pytest.mark.asyncio
    async def test_resolve_public_key_by_kid_for_verify(
        self, profile, in_memory_wallet
    ):
        await in_memory_wallet.create_local_did(KEY, ED25519, self.seed)
        kid = "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"
        key_material = await resolve_public_key_by_kid_for_verify(profile, kid)

        assert key_material == "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
