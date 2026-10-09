"""Tests for external signer dispatch and provider-backed keys."""

from typing import Optional
from unittest.mock import AsyncMock

import pytest
from aries_askar import Key, KeyAlg

from acapy_agent.config.base import InjectionError
from acapy_agent.utils.testing import create_test_profile
from acapy_agent.wallet.askar import AskarWallet
from acapy_agent.wallet.base import BaseWallet
from acapy_agent.wallet.did_info import KeyInfo
from acapy_agent.wallet.did_method import DIDMethods
from acapy_agent.wallet.error import (
    WalletDuplicateError,
    WalletError,
    WalletNotFoundError,
)
from acapy_agent.wallet.kanon_wallet import KanonWallet
from acapy_agent.wallet.key_type import ED25519, P256, KeyTypes
from acapy_agent.wallet.keys.manager import (
    MultikeyManager,
    MultikeyManagerError,
    multikey_to_verkey,
)
from acapy_agent.wallet.signer_registry import Signer, SignerRegistry
from acapy_agent.wallet.util import bytes_to_b58


class _FakeSession:
    """Minimal session stub exposing `inject_or` for the base wallet."""

    def __init__(self, registry: Optional[SignerRegistry] = None):
        self._registry = registry

    def inject_or(self, cls):
        if cls is SignerRegistry:
            return self._registry
        return None


class _StubWallet(BaseWallet):
    """Minimal wallet stub for `_get_external_signature` tests."""

    LOCAL_SIG = b"local-signature"

    def __init__(self, key_info_by_verkey=None, session=None):
        self._by_verkey = key_info_by_verkey or {}
        self._session = session

    async def get_signing_key(self, verkey):
        try:
            return self._by_verkey[verkey]
        except KeyError:
            raise WalletNotFoundError(f"Unknown verkey: {verkey}")

    async def sign_message(self, message, from_verkey):
        # Mirrors the real wallets.
        if (
            sig := await self._get_external_signature(message, from_verkey, self._session)
        ) is not None:
            return sig
        return self.LOCAL_SIG

    # --- Trivial stubs to satisfy BaseWallet ABC ---
    async def create_signing_key(self, *a, **kw): ...
    async def create_key(self, *a, **kw): ...
    async def get_local_did_for_verkey(self, *a, **kw): ...
    async def replace_signing_key_metadata(self, *a, **kw): ...
    async def rotate_did_keypair_start(self, *a, **kw): ...
    async def rotate_did_keypair_apply(self, *a, **kw): ...
    async def create_local_did(self, *a, **kw): ...
    async def store_did(self, *a, **kw): ...
    async def get_public_did(self, *a, **kw): ...
    async def set_public_did(self, *a, **kw): ...
    async def get_local_did(self, *a, **kw): ...
    async def get_local_dids(self, *a, **kw): ...
    async def replace_local_did_metadata(self, *a, **kw): ...
    async def verify_message(self, *a, **kw): ...
    async def pack_message(self, *a, **kw): ...
    async def unpack_message(self, *a, **kw): ...
    async def assign_kid_to_key(self, *a, **kw): ...
    async def get_key_by_kid(self, *a, **kw): ...


def _key_info(verkey: str, metadata: dict) -> KeyInfo:
    return KeyInfo(verkey=verkey, metadata=metadata, key_type=P256)


@pytest.mark.asyncio
async def test_signs_locally_when_verkey_unknown():
    """No key record for verkey → no external signer; wallet signs locally."""
    wallet = _StubWallet()
    assert await wallet.sign_message(b"payload", "unknown") == _StubWallet.LOCAL_SIG


@pytest.mark.asyncio
async def test_signs_locally_when_no_provider_marker():
    """Key exists but no `provider` in metadata → wallet signs locally."""
    verkey = "software-verkey"
    wallet = _StubWallet(key_info_by_verkey={verkey: _key_info(verkey, {})})
    assert await wallet.sign_message(b"payload", verkey) == _StubWallet.LOCAL_SIG


@pytest.mark.asyncio
async def test_signs_locally_when_lookup_fails():
    """A key lookup failure declines rather than breaking signing."""

    class _BrokenWallet(_StubWallet):
        async def get_signing_key(self, verkey):
            raise InjectionError("No instance provided for class: KeyTypes")

    wallet = _BrokenWallet()
    assert await wallet.sign_message(b"payload", "any") == _StubWallet.LOCAL_SIG


@pytest.mark.asyncio
async def test_dispatches_to_registered_signer():
    """`provider` marker + registered Signer → external signature is returned."""
    verkey = "hsm-verkey"
    metadata = {"provider": "hsm", "key_ref": "issuer-key-01"}
    registry = SignerRegistry()
    fake_signer = AsyncMock(spec=Signer)
    fake_signer.sign.return_value = b"\x00" * 64  # fake raw r||s for P-256
    registry.register("hsm", fake_signer)

    wallet = _StubWallet(
        key_info_by_verkey={verkey: _key_info(verkey, metadata)},
        session=_FakeSession(registry),
    )

    sig = await wallet.sign_message(b"payload", verkey)

    assert sig == b"\x00" * 64
    fake_signer.sign.assert_awaited_once_with("issuer-key-01", b"payload", P256)


@pytest.mark.asyncio
async def test_raises_when_provider_marker_but_no_registry():
    """Marker present, no SignerRegistry in context → WalletError."""
    verkey = "hsm-verkey"
    metadata = {"provider": "hsm", "key_ref": "issuer-key-01"}
    wallet = _StubWallet(
        key_info_by_verkey={verkey: _key_info(verkey, metadata)},
        session=_FakeSession(registry=None),
    )
    with pytest.raises(WalletError, match=r"requires provider hsm"):
        await wallet.sign_message(b"payload", verkey)


@pytest.mark.asyncio
async def test_raises_when_provider_unknown():
    """Unknown provider name → WalletError listing the registered names."""
    verkey = "hsm-verkey"
    metadata = {"provider": "unknown-provider", "key_ref": "issuer-key-01"}
    registry = SignerRegistry()
    registry.register("hsm", AsyncMock(spec=Signer))
    wallet = _StubWallet(
        key_info_by_verkey={verkey: _key_info(verkey, metadata)},
        session=_FakeSession(registry),
    )
    with pytest.raises(WalletError, match=r"registered providers: \['hsm'\]"):
        await wallet.sign_message(b"payload", verkey)


@pytest.mark.asyncio
async def test_raises_when_key_ref_missing():
    """Marker present, registry present, no key_ref → WalletError."""
    verkey = "hsm-verkey"
    metadata = {"provider": "hsm"}  # no key_ref
    registry = SignerRegistry()
    registry.register("hsm", AsyncMock(spec=Signer))
    wallet = _StubWallet(
        key_info_by_verkey={verkey: _key_info(verkey, metadata)},
        session=_FakeSession(registry),
    )
    with pytest.raises(WalletError, match="missing key_ref"):
        await wallet.sign_message(b"payload", verkey)


@pytest.mark.asyncio
async def test_insert_public_key_unsupported_by_default():
    with pytest.raises(WalletError, match="does not support public-only keys"):
        await _StubWallet().insert_public_key("verkey", P256)


# --- Real wallet delegation ---


class _HsmSigner:
    """Signer that holds real P-256 keys in memory, keyed by key_ref."""

    def __init__(self):
        self.keys = {}

    async def generate_keypair(self, key_ref, key_type):
        if key_type is not P256:
            raise WalletError(f"Unsupported key type {key_type.key_type}")
        self.keys[key_ref] = Key.generate(KeyAlg.P256)
        return bytes_to_b58(self.keys[key_ref].get_public_bytes())

    async def sign(self, key_ref, message, key_type):
        return self.keys[key_ref].sign_message(message)


async def _askar_profile(registry: Optional[SignerRegistry] = None):
    profile = await create_test_profile()
    profile.context.injector.bind_instance(DIDMethods, DIDMethods())
    profile.context.injector.bind_instance(KeyTypes, KeyTypes())
    if registry:
        profile.context.injector.bind_instance(SignerRegistry, registry)
    return profile


@pytest.mark.asyncio
async def test_askar_wallet_dispatches_to_registered_signer():
    """AskarWallet signs a public-only key through its provider."""
    registry = SignerRegistry()
    signer = _HsmSigner()
    registry.register("hsm", signer)
    profile = await _askar_profile(registry)
    verkey = await signer.generate_keypair("k1", P256)

    async with profile.session() as session:
        wallet = AskarWallet(session)
        await wallet.insert_public_key(
            verkey, P256, metadata={"provider": "hsm", "key_ref": "k1"}
        )
        sig = await wallet.sign_message(b"payload", verkey)
        assert await wallet.verify_message(b"payload", sig, verkey, P256)


@pytest.mark.asyncio
async def test_askar_wallet_signs_locally_without_marker():
    """No marker → AskarWallet signs with its own key and never calls the signer."""
    registry = SignerRegistry()
    fake_signer = AsyncMock(spec=Signer)
    registry.register("hsm", fake_signer)
    profile = await _askar_profile(registry)

    async with profile.session() as session:
        wallet = AskarWallet(session)
        key_info = await wallet.create_key(ED25519)
        sig = await wallet.sign_message(b"payload", key_info.verkey)
        assert await wallet.verify_message(b"payload", sig, key_info.verkey, ED25519)

    fake_signer.sign.assert_not_awaited()


@pytest.mark.asyncio
async def test_askar_insert_public_key_is_findable_by_multikey_and_kid():
    signer = _HsmSigner()
    verkey = await signer.generate_keypair("k1", P256)
    profile = await _askar_profile()

    async with profile.session() as session:
        wallet = AskarWallet(session)
        await wallet.insert_public_key(
            verkey, P256, metadata={"provider": "hsm", "key_ref": "k1"}, kid="kid-1"
        )
        manager = MultikeyManager(session)
        multikey = (await manager.from_kid("kid-1"))["multikey"]
        assert multikey_to_verkey(multikey) == verkey
        assert (await manager.from_multikey(multikey))["kid"] == "kid-1"

        with pytest.raises(WalletDuplicateError):
            await wallet.insert_public_key(verkey, P256)


@pytest.mark.asyncio
async def test_askar_insert_public_key_rejects_invalid_verkey():
    profile = await _askar_profile()
    async with profile.session() as session:
        with pytest.raises(WalletError, match="Invalid p256 verkey"):
            await AskarWallet(session).insert_public_key(bytes_to_b58(b"bad"), P256)


@pytest.mark.asyncio
async def test_askar_kid_binding_keeps_provider_metadata():
    """Binding and unbinding a kid must not drop provider and key_ref."""
    signer = _HsmSigner()
    verkey = await signer.generate_keypair("k1", P256)
    metadata = {"provider": "hsm", "key_ref": "k1"}
    profile = await _askar_profile()

    async with profile.session() as session:
        wallet = AskarWallet(session)
        await wallet.insert_public_key(verkey, P256, metadata=metadata)

        await wallet.assign_kid_to_key(verkey, "did:web:example.com#key-1")
        assert (await wallet.get_signing_key(verkey)).metadata == metadata

        await wallet.unassign_kid_from_key(verkey, "did:web:example.com#key-1")
        assert (await wallet.get_signing_key(verkey)).metadata == metadata


@pytest.mark.asyncio
async def test_askar_replace_metadata_keeps_external_signer_fields():
    signer = _HsmSigner()
    verkey = await signer.generate_keypair("k1", P256)
    metadata = {"provider": "hsm", "key_ref": "k1"}
    profile = await _askar_profile()

    async with profile.session() as session:
        wallet = AskarWallet(session)
        await wallet.insert_public_key(verkey, P256, metadata=metadata)

        await wallet.replace_signing_key_metadata(verkey, {**metadata, "note": "x"})
        assert (await wallet.get_signing_key(verkey)).metadata == {
            **metadata,
            "note": "x",
        }

        for bad in ({"note": "x"}, {**metadata, "key_ref": "k2"}):
            with pytest.raises(WalletError, match="cannot change"):
                await wallet.replace_signing_key_metadata(verkey, bad)
        assert (await wallet.get_signing_key(verkey)).metadata["key_ref"] == "k1"

        local = await wallet.create_key(ED25519)
        with pytest.raises(WalletError, match="cannot change"):
            await wallet.replace_signing_key_metadata(
                local.verkey, {"provider": "hsm", "key_ref": "k1"}
            )
        await wallet.replace_signing_key_metadata(local.verkey, {"note": "y"})
        assert (await wallet.get_signing_key(local.verkey)).metadata == {"note": "y"}


@pytest.mark.asyncio
async def test_create_key_with_provider():
    registry = SignerRegistry()
    signer = _HsmSigner()
    registry.register("hsm", signer)
    profile = await _askar_profile(registry)

    async with profile.session() as session:
        result = await MultikeyManager(session).create(
            alg="p256", provider="hsm", kid="kid-1"
        )
        verkey = multikey_to_verkey(result["multikey"])
        wallet = AskarWallet(session)
        key_info = await wallet.get_signing_key(verkey)
        sig = await wallet.sign_message(b"payload", verkey)
        assert await wallet.verify_message(b"payload", sig, verkey, P256)

    assert result["kid"] == "kid-1"
    assert key_info.metadata["provider"] == "hsm"
    assert key_info.metadata["key_ref"] in signer.keys


@pytest.mark.asyncio
async def test_create_key_with_provider_rejects_bad_requests():
    registry = SignerRegistry()
    signer = _HsmSigner()
    registry.register("hsm", signer)
    profile = await _askar_profile(registry)

    async with profile.session() as session:
        manager = MultikeyManager(session)
        with pytest.raises(MultikeyManagerError, match="Unknown provider"):
            await manager.create(alg="p256", provider="missing")
        with pytest.raises(MultikeyManagerError, match="seed cannot be used"):
            await manager.create(
                alg="p256", provider="hsm", seed="00000000000000000000000000000000"
            )
        with pytest.raises(MultikeyManagerError, match="could not create the key"):
            await manager.create(alg="ed25519", provider="hsm")

    assert signer.keys == {}


@pytest.mark.asyncio
async def test_kanon_wallet_dispatches_to_registered_signer():
    """KanonWallet returns the external signature when the key names a provider."""
    verkey = "hsm-verkey"
    registry = SignerRegistry()
    fake_signer = AsyncMock(spec=Signer)
    fake_signer.sign.return_value = b"\x04" * 64
    registry.register("hsm", fake_signer)

    wallet = KanonWallet(_FakeSession(registry))
    wallet.get_signing_key = AsyncMock(
        return_value=_key_info(verkey, {"provider": "hsm", "key_ref": "k1"})
    )

    assert await wallet.sign_message(b"payload", verkey) == b"\x04" * 64
    fake_signer.sign.assert_awaited_once_with("k1", b"payload", P256)


# --- SignerRegistry unit tests ---


def test_signer_registry_register_and_get():
    reg = SignerRegistry()
    signer = AsyncMock(spec=Signer)
    reg.register("hsm", signer)
    assert reg.get("hsm") is signer
    assert reg.names() == ["hsm"]


def test_signer_registry_get_returns_none_for_unknown():
    reg = SignerRegistry()
    assert reg.get("unknown") is None


def test_signer_registry_rejects_duplicate_registration():
    reg = SignerRegistry()
    reg.register("hsm", AsyncMock(spec=Signer))
    with pytest.raises(ValueError, match="already registered"):
        reg.register("hsm", AsyncMock(spec=Signer))
