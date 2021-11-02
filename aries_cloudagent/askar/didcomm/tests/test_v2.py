import json

from asynctest import mock as async_mock
import pytest

from aries_askar import AskarError, Key, KeyAlg, Session

from ....config.injection_context import InjectionContext
from ....utils.jwe import JweRecipient, b64url, JweEnvelope

from ...profile import AskarProfileManager
from .. import v2 as test_module


ALICE_KID = "did:example:alice#key-1"
BOB_KID = "did:example:bob#key-1"
CAROL_KID = "did:example:carol#key-2"
MESSAGE = b"Expecto patronum"


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
        carol_sk = Key.generate(KeyAlg.P256)  # testing mixed recipient key types
        carol_pk = Key.from_jwk(carol_sk.get_jwk_public())

        enc_message = test_module.ecdh_es_encrypt(
            {BOB_KID: bob_pk, CAROL_KID: carol_pk}, MESSAGE
        )

        # receiver must have the private keypair accessible
        await session.insert_key("my_sk", bob_sk, tags={"kid": BOB_KID})

        plaintext, recip_kid, sender_kid = await test_module.unpack_message(
            session, enc_message
        )
        assert recip_kid == BOB_KID
        assert sender_kid is None
        assert plaintext == MESSAGE

    @pytest.mark.asyncio
    async def test_es_encrypt_x(self, session: Session):
        alg = KeyAlg.X25519
        bob_sk = Key.generate(alg)
        bob_pk = Key.from_jwk(bob_sk.get_jwk_public())

        with pytest.raises(
            test_module.DidcommEnvelopeError, match="No message recipients"
        ):
            _ = test_module.ecdh_es_encrypt({}, MESSAGE)

        with async_mock.patch(
            "aries_askar.Key.generate",
            async_mock.MagicMock(side_effect=AskarError(99, "")),
        ):
            with pytest.raises(
                test_module.DidcommEnvelopeError,
                match="Error creating content encryption key",
            ):
                _ = test_module.ecdh_es_encrypt({BOB_KID: bob_pk}, MESSAGE)

        with async_mock.patch(
            "aries_askar.Key.aead_encrypt",
            async_mock.MagicMock(side_effect=AskarError(99, "")),
        ):
            with pytest.raises(
                test_module.DidcommEnvelopeError,
                match="Error encrypting",
            ):
                _ = test_module.ecdh_es_encrypt({BOB_KID: bob_pk}, MESSAGE)

    @pytest.mark.asyncio
    async def test_es_decrypt_x(self):
        alg = KeyAlg.X25519
        bob_sk = Key.generate(alg)

        message_unknown_alg = JweEnvelope(
            protected={"alg": "NOT-SUPPORTED"},
        )
        message_unknown_alg.add_recipient(
            JweRecipient(encrypted_key=b"0000", header={"kid": BOB_KID})
        )
        with pytest.raises(
            test_module.DidcommEnvelopeError,
            match="Unsupported ECDH-ES algorithm",
        ):
            _ = test_module.ecdh_es_decrypt(
                message_unknown_alg,
                BOB_KID,
                bob_sk,
            )

        message_unknown_enc = JweEnvelope(
            protected={"alg": "ECDH-ES+A128KW", "enc": "UNKNOWN"},
        )
        message_unknown_enc.add_recipient(
            JweRecipient(encrypted_key=b"0000", header={"kid": BOB_KID})
        )
        with pytest.raises(
            test_module.DidcommEnvelopeError,
            match="Unsupported ECDH-ES content encryption",
        ):
            _ = test_module.ecdh_es_decrypt(
                message_unknown_enc,
                BOB_KID,
                bob_sk,
            )

        message_invalid_epk = JweEnvelope(
            protected={"alg": "ECDH-ES+A128KW", "enc": "A256GCM", "epk": {}},
        )
        message_invalid_epk.add_recipient(
            JweRecipient(encrypted_key=b"0000", header={"kid": BOB_KID})
        )
        with pytest.raises(
            test_module.DidcommEnvelopeError,
            match="Error loading ephemeral key",
        ):
            _ = test_module.ecdh_es_decrypt(
                message_invalid_epk,
                BOB_KID,
                bob_sk,
            )

    @pytest.mark.asyncio
    async def test_1pu_round_trip(self, session: Session):
        alg = KeyAlg.X25519
        alice_sk = Key.generate(alg)
        alice_pk = Key.from_jwk(alice_sk.get_jwk_public())
        bob_sk = Key.generate(alg)
        bob_pk = Key.from_jwk(bob_sk.get_jwk_public())

        enc_message = test_module.ecdh_1pu_encrypt(
            {BOB_KID: bob_pk}, ALICE_KID, alice_sk, MESSAGE
        )

        # receiver must have the private keypair accessible
        await session.insert_key("my_sk", bob_sk, tags={"kid": BOB_KID})
        # for now at least, insert the sender public key so it can be resolved
        await session.insert_key("alice_pk", alice_pk, tags={"kid": ALICE_KID})

        plaintext, recip_kid, sender_kid = await test_module.unpack_message(
            session, enc_message
        )
        assert recip_kid == BOB_KID
        assert sender_kid == ALICE_KID
        assert plaintext == MESSAGE

    @pytest.mark.asyncio
    async def test_1pu_encrypt_x(self, session: Session):
        alg = KeyAlg.X25519
        alice_sk = Key.generate(alg)
        bob_sk = Key.generate(alg)
        bob_pk = Key.from_jwk(bob_sk.get_jwk_public())

        with pytest.raises(
            test_module.DidcommEnvelopeError, match="No message recipients"
        ):
            _ = test_module.ecdh_1pu_encrypt({}, ALICE_KID, alice_sk, MESSAGE)

        alt_sk = Key.generate(KeyAlg.P256)
        alt_pk = Key.from_jwk(alt_sk.get_jwk_public())
        with pytest.raises(
            test_module.DidcommEnvelopeError, match="key types must be consistent"
        ):
            _ = test_module.ecdh_1pu_encrypt(
                {BOB_KID: bob_pk, "alt": alt_pk}, ALICE_KID, alice_sk, MESSAGE
            )

        with async_mock.patch(
            "aries_askar.Key.generate",
            async_mock.MagicMock(side_effect=AskarError(99, "")),
        ):
            with pytest.raises(
                test_module.DidcommEnvelopeError,
                match="Error creating content encryption key",
            ):
                _ = test_module.ecdh_1pu_encrypt(
                    {BOB_KID: bob_pk}, ALICE_KID, alice_sk, MESSAGE
                )

        with async_mock.patch(
            "aries_askar.Key.aead_encrypt",
            async_mock.MagicMock(side_effect=AskarError(99, "")),
        ):
            with pytest.raises(
                test_module.DidcommEnvelopeError,
                match="Error encrypting",
            ):
                _ = test_module.ecdh_1pu_encrypt(
                    {BOB_KID: bob_pk}, ALICE_KID, alice_sk, MESSAGE
                )

    @pytest.mark.asyncio
    async def test_1pu_decrypt_x(self):
        alg = KeyAlg.X25519
        alice_sk = Key.generate(alg)
        alice_pk = Key.from_jwk(alice_sk.get_jwk_public())
        bob_sk = Key.generate(alg)

        message_unknown_alg = JweEnvelope(
            protected={"alg": "NOT-SUPPORTED"},
        )
        message_unknown_alg.add_recipient(
            JweRecipient(encrypted_key=b"0000", header={"kid": BOB_KID})
        )
        with pytest.raises(
            test_module.DidcommEnvelopeError,
            match="Unsupported ECDH-1PU algorithm",
        ):
            _ = test_module.ecdh_1pu_decrypt(
                message_unknown_alg,
                BOB_KID,
                bob_sk,
                alice_pk,
            )

        message_unknown_enc = JweEnvelope(
            protected={"alg": "ECDH-1PU+A128KW", "enc": "UNKNOWN"},
        )
        message_unknown_enc.add_recipient(
            JweRecipient(encrypted_key=b"0000", header={"kid": BOB_KID})
        )
        with pytest.raises(
            test_module.DidcommEnvelopeError,
            match="Unsupported ECDH-1PU content encryption",
        ):
            _ = test_module.ecdh_1pu_decrypt(
                message_unknown_enc, BOB_KID, bob_sk, alice_pk
            )

        message_invalid_epk = JweEnvelope(
            protected={"alg": "ECDH-1PU+A128KW", "enc": "A256CBC-HS512", "epk": {}},
        )
        message_invalid_epk.add_recipient(
            JweRecipient(encrypted_key=b"0000", header={"kid": BOB_KID})
        )
        with pytest.raises(
            test_module.DidcommEnvelopeError,
            match="Error loading ephemeral key",
        ):
            _ = test_module.ecdh_1pu_decrypt(
                message_invalid_epk,
                BOB_KID,
                bob_sk,
                alice_pk,
            )

    @pytest.mark.asyncio
    async def test_unpack_message_any_x(self, session: Session):
        message_invalid = "{}"

        with pytest.raises(
            test_module.DidcommEnvelopeError,
            match="Invalid",
        ):
            _ = await test_module.unpack_message(session, message_invalid)

        message_unknown_alg = json.dumps(
            {
                "protected": b64url(json.dumps({"alg": "NOT-SUPPORTED"})),
                "recipients": [{"header": {"kid": "bob"}, "encrypted_key": "MTIzNA"}],
                "iv": "MTIzNA",
                "ciphertext": "MTIzNA",
                "tag": "MTIzNA",
            }
        )

        with pytest.raises(
            test_module.DidcommEnvelopeError,
            match="Unsupported DIDComm encryption",
        ):
            _ = await test_module.unpack_message(session, message_unknown_alg)

        message_unknown_recip = json.dumps(
            {
                "protected": b64url(json.dumps({"alg": "ECDH-ES+A128KW"})),
                "recipients": [{"header": {"kid": "bob"}, "encrypted_key": "MTIzNA"}],
                "iv": "MTIzNA",
                "ciphertext": "MTIzNA",
                "tag": "MTIzNA",
            }
        )

        with pytest.raises(
            test_module.DidcommEnvelopeError,
            match="No recognized recipient key",
        ):
            _ = await test_module.unpack_message(session, message_unknown_recip)

    @pytest.mark.asyncio
    async def test_unpack_message_1pu_x(self, session: Session):
        alg = KeyAlg.X25519
        alice_sk = Key.generate(alg)
        alice_pk = Key.from_jwk(alice_sk.get_jwk_public())
        bob_sk = Key.generate(alg)
        bob_pk = Key.from_jwk(bob_sk.get_jwk_public())

        # receiver must have the private keypair accessible
        await session.insert_key("my_sk", bob_sk, tags={"kid": BOB_KID})
        # for now at least, insert the sender public key so it can be resolved
        await session.insert_key("alice_pk", alice_pk, tags={"kid": ALICE_KID})

        message_1pu_no_skid = json.dumps(
            {
                "protected": b64url(json.dumps({"alg": "ECDH-1PU+A128KW"})),
                "recipients": [{"header": {"kid": BOB_KID}, "encrypted_key": "MTIzNA"}],
                "iv": "MTIzNA",
                "ciphertext": "MTIzNA",
                "tag": "MTIzNA",
            }
        )

        with pytest.raises(
            test_module.DidcommEnvelopeError,
            match="Sender key ID not provided",
        ):
            _ = await test_module.unpack_message(session, message_1pu_no_skid)

        message_1pu_unknown_skid = json.dumps(
            {
                "protected": b64url(
                    json.dumps({"alg": "ECDH-1PU+A128KW", "skid": "UNKNOWN"})
                ),
                "recipients": [{"header": {"kid": BOB_KID}, "encrypted_key": "MTIzNA"}],
                "iv": "MTIzNA",
                "ciphertext": "MTIzNA",
                "tag": "MTIzNA",
            }
        )

        with pytest.raises(
            test_module.DidcommEnvelopeError,
            match="Sender public key not found",
        ):
            _ = await test_module.unpack_message(session, message_1pu_unknown_skid)

        message_1pu_apu_invalid = json.dumps(
            {
                "protected": b64url(
                    json.dumps({"alg": "ECDH-1PU+A128KW", "skid": "A", "apu": "A"})
                ),
                "recipients": [{"header": {"kid": BOB_KID}, "encrypted_key": "MTIzNA"}],
                "iv": "MTIzNA",
                "ciphertext": "MTIzNA",
                "tag": "MTIzNA",
            }
        )

        with pytest.raises(
            test_module.DidcommEnvelopeError,
            match="Invalid apu value",
        ):
            _ = await test_module.unpack_message(session, message_1pu_apu_invalid)

        message_1pu_apu_mismatch = json.dumps(
            {
                "protected": b64url(
                    json.dumps(
                        {
                            "alg": "ECDH-1PU+A128KW",
                            "skid": ALICE_KID,
                            "apu": b64url("UNKNOWN"),
                        }
                    )
                ),
                "recipients": [{"header": {"kid": BOB_KID}, "encrypted_key": "MTIzNA"}],
                "iv": "MTIzNA",
                "ciphertext": "MTIzNA",
                "tag": "MTIzNA",
            }
        )

        with pytest.raises(
            test_module.DidcommEnvelopeError,
            match="Mismatch between skid and apu",
        ):
            _ = await test_module.unpack_message(session, message_1pu_apu_mismatch)
