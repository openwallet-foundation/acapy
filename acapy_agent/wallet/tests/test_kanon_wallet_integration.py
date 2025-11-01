import os

import pytest
import pytest_asyncio

from ...core.profile import Profile
from ...ledger.base import BaseLedger
from ...tests import mock
from ...utils.testing import create_test_profile
from ..did_method import INDY, SOV, WEB
from ..error import WalletDuplicateError, WalletError, WalletNotFoundError
from ..kanon_wallet import KanonWallet
from ..key_type import ED25519

# Skip all tests if POSTGRES_URL is not set
if not os.getenv("POSTGRES_URL"):
    pytest.skip(
        "Kanon PostgreSQL integration tests disabled: set POSTGRES_URL to enable",
        allow_module_level=True,
    )

pytestmark = [pytest.mark.postgres, pytest.mark.p1]


@pytest_asyncio.fixture
async def profile():
    postgres_url = os.getenv("POSTGRES_URL")
    profile = await create_test_profile(
        settings={
            "wallet.type": "kanon-anoncreds",
            "wallet.storage_type": "postgres",
            "wallet.storage_config": {"url": postgres_url},
            "wallet.storage_creds": {
                "account": "postgres",
                "password": "postgres",
            },
            "dbstore.storage_type": "postgres",
            "dbstore.storage_config": {"url": postgres_url},
            "dbstore.storage_creds": {
                "account": "postgres",
                "password": "postgres",
            },
            "dbstore.schema_config": "normalize",
        }
    )
    yield profile
    # Cleanup happens automatically


@pytest_asyncio.fixture
async def wallet(profile: Profile):
    async with profile.session() as session:
        yield KanonWallet(session)


@pytest.mark.asyncio
async def test_create_local_did(wallet: KanonWallet):
    metadata = {"description": "Test DID", "public": False}
    did_info = await wallet.create_local_did(
        method=SOV,
        key_type=ED25519,
        metadata=metadata,
    )

    assert did_info.did
    assert did_info.verkey
    assert did_info.metadata == metadata
    assert did_info.method == SOV
    assert did_info.key_type == ED25519

    retrieved = await wallet.get_local_did(did_info.did)
    assert retrieved.did == did_info.did
    assert retrieved.verkey == did_info.verkey
    assert retrieved.metadata == metadata


@pytest.mark.asyncio
async def test_create_public_did(wallet: KanonWallet):
    did_info = await wallet.create_local_did(
        method=SOV,
        key_type=ED25519,
        metadata={"public": True},
    )

    await wallet.set_public_did(did_info.did)

    public_did = await wallet.get_public_did()
    assert public_did is not None
    assert public_did.did == did_info.did
    assert public_did.verkey == did_info.verkey


@pytest.mark.asyncio
async def test_rotate_keypair(wallet: KanonWallet):
    did_info = await wallet.create_local_did(
        method=SOV,
        key_type=ED25519,
    )
    old_verkey = did_info.verkey

    new_verkey = await wallet.rotate_did_keypair_start(did_info.did)
    await wallet.rotate_did_keypair_apply(did_info.did)

    assert new_verkey != old_verkey

    updated_did = await wallet.get_local_did(did_info.did)
    assert updated_did.verkey == new_verkey

    message = b"test message after rotation"
    signature = await wallet.sign_message(message, new_verkey)
    assert signature

    assert updated_did.verkey != old_verkey


@pytest.mark.asyncio
async def test_get_all_local_dids(wallet: KanonWallet):
    did_infos = []
    for i in range(3):
        did_info = await wallet.create_local_did(
            method=SOV,
            key_type=ED25519,
            metadata={"index": i, "description": f"Test DID {i}"},
        )
        did_infos.append(did_info)

    all_dids = await wallet.get_local_dids()

    created_dids = {di.did for di in did_infos}
    retrieved_dids = {di.did for di in all_dids}
    assert created_dids.issubset(retrieved_dids)

    test_did = next(di for di in all_dids if di.did == did_infos[0].did)
    assert test_did.verkey == did_infos[0].verkey
    assert test_did.metadata.get("index") == 0


@pytest.mark.asyncio
async def test_sign_message(wallet: KanonWallet):
    did_info = await wallet.create_local_did(
        method=SOV,
        key_type=ED25519,
    )

    message = b"Hello, World!"
    signature = await wallet.sign_message(message, did_info.verkey)

    assert signature
    assert isinstance(signature, bytes)

    valid = await wallet.verify_message(message, signature, did_info.verkey, ED25519)
    assert valid

    message2 = b"Different message"
    signature2 = await wallet.sign_message(message2, did_info.verkey)
    assert signature2 != signature


@pytest.mark.asyncio
async def test_verify_message(wallet: KanonWallet):
    did_info = await wallet.create_local_did(
        method=SOV,
        key_type=ED25519,
    )

    message = b"Test message for verification"
    signature = await wallet.sign_message(message, did_info.verkey)

    valid = await wallet.verify_message(message, signature, did_info.verkey, ED25519)
    assert valid is True

    invalid_sig = b"invalid signature bytes"
    valid = await wallet.verify_message(message, invalid_sig, did_info.verkey, ED25519)
    assert valid is False

    wrong_message = b"Wrong message content"
    valid = await wallet.verify_message(
        wrong_message, signature, did_info.verkey, ED25519
    )
    assert valid is False


@pytest.mark.asyncio
async def test_pack_message(wallet: KanonWallet):
    sender = await wallet.create_local_did(
        method=SOV,
        key_type=ED25519,
    )
    recipient = await wallet.create_local_did(
        method=SOV,
        key_type=ED25519,
    )

    message = b"Secret message content"
    packed = await wallet.pack_message(message, [recipient.verkey], sender.verkey)

    assert packed
    assert isinstance(packed, bytes)

    assert packed != message

    assert len(packed) > len(message)


@pytest.mark.asyncio
async def test_unpack_message(wallet: KanonWallet):
    sender = await wallet.create_local_did(
        method=SOV,
        key_type=ED25519,
    )
    recipient = await wallet.create_local_did(
        method=SOV,
        key_type=ED25519,
    )

    original_message = b"Test message for pack/unpack"
    packed = await wallet.pack_message(
        original_message, [recipient.verkey], sender.verkey
    )
    message, from_verkey, to_verkey = await wallet.unpack_message(packed)

    assert message == original_message.decode("utf-8")
    assert from_verkey == sender.verkey
    assert to_verkey == recipient.verkey


@pytest.mark.asyncio
async def test_set_public_did(wallet: KanonWallet):
    did1 = await wallet.create_local_did(method=SOV, key_type=ED25519)
    did2 = await wallet.create_local_did(method=SOV, key_type=ED25519)

    await wallet.set_public_did(did1.did)
    public = await wallet.get_public_did()
    assert public.did == did1.did

    await wallet.set_public_did(did2.did)
    public = await wallet.get_public_did()
    assert public.did == did2.did

    assert public.did != did1.did


@pytest.mark.asyncio
async def test_replace_local_did_metadata(wallet: KanonWallet):
    initial_metadata = {"description": "Initial", "version": 1}
    did_info = await wallet.create_local_did(
        method=SOV,
        key_type=ED25519,
        metadata=initial_metadata,
    )

    retrieved = await wallet.get_local_did(did_info.did)
    assert retrieved.metadata == initial_metadata

    new_metadata = {"description": "Updated", "version": 2, "active": True}
    await wallet.replace_local_did_metadata(did_info.did, new_metadata)

    updated = await wallet.get_local_did(did_info.did)
    assert updated.metadata == new_metadata
    assert updated.metadata != initial_metadata
    assert updated.metadata["version"] == 2


@pytest.mark.asyncio
async def test_get_local_did_by_verkey(wallet: KanonWallet):
    metadata = {"description": "Test for verkey lookup"}
    did_info = await wallet.create_local_did(
        method=SOV,
        key_type=ED25519,
        metadata=metadata,
    )

    retrieved = await wallet.get_local_did_for_verkey(did_info.verkey)

    assert retrieved.did == did_info.did
    assert retrieved.verkey == did_info.verkey
    assert retrieved.metadata == metadata

    with pytest.raises(WalletNotFoundError):
        await wallet.get_local_did_for_verkey("NonExistentVerkey123")


@pytest.mark.asyncio
async def test_set_did_endpoint(wallet: KanonWallet):
    mock_ledger = mock.MagicMock(BaseLedger, autospec=True)

    sov_did_info = await wallet.create_local_did(
        method=SOV,
        key_type=ED25519,
    )

    await wallet.set_public_did(sov_did_info.did)

    original_replace = wallet.replace_local_did_metadata
    wallet.replace_local_did_metadata = mock.CoroutineMock()

    await wallet.set_did_endpoint(
        sov_did_info.did,
        "http://example.com",
        mock_ledger,
    )

    wallet.replace_local_did_metadata = original_replace

    indy_did_info = await wallet.create_local_did(
        method=INDY,
        key_type=ED25519,
    )

    await wallet.set_public_did(indy_did_info.did)

    wallet.replace_local_did_metadata = mock.CoroutineMock()
    await wallet.set_did_endpoint(
        indy_did_info.did,
        "http://example.com",
        mock_ledger,
    )
    wallet.replace_local_did_metadata = original_replace

    import uuid

    web_did_info = await wallet.create_local_did(
        method=WEB,
        key_type=ED25519,
        did=f"did:web:example.com:test-{uuid.uuid4()}",
    )

    await wallet.set_public_did(web_did_info.did)

    with pytest.raises(WalletError):
        await wallet.set_did_endpoint(
            web_did_info.did,
            "http://example.com",
            mock_ledger,
        )


@pytest.mark.asyncio
async def test_duplicate_did_error(wallet: KanonWallet):
    seed = "000000000000000000000000Wallet01"
    did_info1 = await wallet.create_local_did(
        method=SOV,
        key_type=ED25519,
        seed=seed,
        metadata={"original": True},
    )

    try:
        did_info2 = await wallet.create_local_did(
            method=SOV,
            key_type=ED25519,
            seed=seed,
            metadata={"original": False},
        )
        assert did_info2.did == did_info1.did
    except WalletDuplicateError:
        pass

    retrieved = await wallet.get_local_did(did_info1.did)
    assert retrieved.did == did_info1.did


@pytest.mark.asyncio
async def test_get_nonexistent_did_error(wallet: KanonWallet):
    with pytest.raises(WalletNotFoundError):
        await wallet.get_local_did("NonExistentDID123456")

    with pytest.raises(WalletNotFoundError):
        await wallet.get_local_did_for_verkey("NonExistentVerkey123456")
