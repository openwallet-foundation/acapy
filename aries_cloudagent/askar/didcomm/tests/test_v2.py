from aries_askar.store import Session
import pytest

from aries_askar import Key, KeyAlg

from ....config.injection_context import InjectionContext

from ...profile import AskarProfileManager
from .. import v2 as test_module


@pytest.fixture()
async def session():
    context = InjectionContext()
    profile = await AskarProfileManager().provision(
        context,
        {
            "name": ":memory:",
            "key": await AskarProfileManager.generate_store_key(),
            "key_derivation_method": "RAW",  # much faster than using argon-hashed keys
        },
    )
    async with profile.session() as session:
        yield session.handle
    del session
    await profile.close()


@pytest.mark.askar
class TestAskarDidCommV2:
    @pytest.mark.asyncio
    async def test_es_round_trip(self, session: Session):
        alg = KeyAlg.X25519
        bob_sk = Key.generate(alg)
        bob_pk = Key.from_jwk(bob_sk.get_jwk_public())
        bob_kid = "did:example:bob#key-1"
        message = b"Expecto patronum"

        enc_message = test_module.ecdh_es_encrypt({bob_kid: bob_pk}, message)

        # receiver must have the private keypair accessible
        await session.insert_key("my_sk", bob_sk, tags={"kid": bob_kid})

        plaintext, recip_kid, sender_kid = await test_module.unpack_message(
            session, enc_message
        )
        assert recip_kid == bob_kid
        assert sender_kid is None
        assert plaintext == message

    @pytest.mark.asyncio
    async def test_1pu_round_trip(self, session: Session):
        alg = KeyAlg.X25519
        alice_sk = Key.generate(alg)
        alice_pk = Key.from_jwk(alice_sk.get_jwk_public())
        alice_kid = "did:example:alice#key-1"
        bob_sk = Key.generate(alg)
        bob_pk = Key.from_jwk(bob_sk.get_jwk_public())
        bob_kid = "did:example:bob#key-1"
        alice_pk, bob_pk = alice_sk, bob_sk
        message = b"Expecto patronum"

        # receiver must have the private keypair accessible
        await session.insert_key("my_sk", bob_sk, tags={"kid": bob_kid})
        # for now at least, insert the sender public key so it can be resolved
        await session.insert_key("alice_pk", alice_pk, tags={"kid": alice_kid})

        enc_message = test_module.ecdh_1pu_encrypt(
            {bob_kid: bob_pk}, alice_kid, alice_sk, message
        )

        plaintext, recip_kid, sender_kid = await test_module.unpack_message(
            session, enc_message
        )
        assert recip_kid == bob_kid
        assert sender_kid == alice_kid
        assert plaintext == message
