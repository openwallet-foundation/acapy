"""Multikey class."""

import logging
from ...core.profile import ProfileSession
from ...resolver.did_resolver import DIDResolver
from ...utils.multiformats import multibase
from ...wallet.error import WalletError, WalletNotFoundError
from ..base import BaseWallet
from ..key_type import BLS12381G2, ED25519, P256, KeyType
from ..util import b58_to_bytes, bytes_to_b58
from pydid import VerificationMethod

LOGGER = logging.getLogger(__name__)

DEFAULT_ALG = "ed25519"
ALG_MAPPINGS = {
    "ed25519": {
        "key_type": ED25519,
        "multikey_prefix": "z6Mk",
        "prefix_hex": "ed01",
        "prefix_length": 2,
    },
    "x25519": {
        "key_type": ED25519,
        "multikey_prefix": "z6LS",
        "prefix_hex": "ec01",
        "prefix_length": 2,
    },
    "p256": {
        "key_type": P256,
        "multikey_prefix": "zDn",
        "prefix_hex": "8024",
        "prefix_length": 2,
    },
    "bls12381g2": {
        "key_type": BLS12381G2,
        "multikey_prefix": "zUC7",
        "prefix_hex": "eb01",
        "prefix_length": 2,
    },
}


def multikey_to_verkey(multikey: str):
    """Transform multikey to verkey."""

    alg = key_type_from_multikey(multikey).key_type
    prefix_length = ALG_MAPPINGS[alg]["prefix_length"]
    public_bytes = bytes(bytearray(multibase.decode(multikey))[prefix_length:])

    return bytes_to_b58(public_bytes)


def verkey_to_multikey(verkey: str, alg: str):
    """Transform verkey to multikey."""

    prefix_hex = ALG_MAPPINGS[alg]["prefix_hex"]
    prefixed_key_hex = f"{prefix_hex}{b58_to_bytes(verkey).hex()}"

    return multibase.encode(bytes.fromhex(prefixed_key_hex), "base58btc")


def key_type_from_multikey(multikey: str) -> KeyType:
    """Derive key_type class from multikey prefix."""
    for mapping in ALG_MAPPINGS:
        if multikey.startswith(ALG_MAPPINGS[mapping]["multikey_prefix"]):
            return ALG_MAPPINGS[mapping]["key_type"]

    raise MultikeyManagerError(f"Unsupported key algorithm for multikey {multikey}.")


def multikey_from_verification_method(verification_method: VerificationMethod) -> str:
    """Derive a multikey from a VerificationMethod."""
    if verification_method.type == "Multikey":
        multikey = verification_method.public_key_multibase

    elif verification_method.type == "Ed25519VerificationKey2018":
        multikey = verkey_to_multikey(
            verification_method.public_key_base58, alg="ed25519"
        )

    elif verification_method.type == "Ed25519VerificationKey2020":
        multikey = verification_method.public_key_multibase

    elif verification_method.type == "Bls12381G2Key2020":
        multikey = verkey_to_multikey(
            verification_method.public_key_base58, alg="bls12381g2"
        )
    # TODO address JsonWebKey based verification methods

    else:
        raise MultikeyManagerError("Unknown verification method type.")

    return multikey


class MultikeyManagerError(Exception):
    """Generic MultikeyManager Error."""


class MultikeyManager:
    """Class for managing wallet keys."""

    def __init__(self, session: ProfileSession):
        """Initialize the MultikeyManager."""

        self.session: ProfileSession = session
        self.wallet: BaseWallet = session.inject(BaseWallet)

    async def resolve_and_bind_kid(self, kid: str):
        """Fetch key if exists, otherwise resolve and bind it.

        This function is idempotent.
        """
        if await self.kid_exists(kid):
            LOGGER.info(f"kid {kid} already bound in storage, will not resolve.")
            return await self.from_kid(kid)
        else:
            multikey = await self.resolve_multikey_from_verification_method_id(kid)
            LOGGER.info(
                f"kid {kid} binding not found in storage, \
                binding to resolved multikey {multikey}."
            )
            return await self.update(multikey, kid)

    async def resolve_multikey_from_verification_method_id(self, kid: str):
        """Derive a multikey from the verification method ID."""
        resolver = self.session.inject(DIDResolver)
        verification_method = await resolver.dereference(
            profile=self.session.profile, did_url=kid
        )

        return multikey_from_verification_method(verification_method)

    def key_type_from_multikey(self, multikey: str) -> KeyType:
        """Derive key_type class from multikey prefix."""
        for mapping in ALG_MAPPINGS:
            if multikey.startswith(ALG_MAPPINGS[mapping]["multikey_prefix"]):
                return ALG_MAPPINGS[mapping]["key_type"]

        raise MultikeyManagerError(f"Unsupported key algorithm for multikey {multikey}.")

    async def kid_exists(self, kid: str):
        """Check if kid exists."""

        try:
            key = await self.wallet.get_key_by_kid(kid=kid)

            if key:
                return True
            return False

        except (WalletNotFoundError, AttributeError):
            return False

    async def multikey_exists(self, multikey: str):
        """Check if a multikey exists in the wallet."""

        try:
            key_info = await self.wallet.get_signing_key(
                verkey=multikey_to_verkey(multikey)
            )

            if key_info:
                return True
            return False

        except (WalletNotFoundError, AttributeError):
            return False

    async def from_kid(self, kid: str):
        """Fetch a single key."""

        try:
            key_info = await self.wallet.get_key_by_kid(kid=kid)

            return {
                "kid": key_info.kid,
                "multikey": verkey_to_multikey(
                    key_info.verkey, alg=key_info.key_type.key_type
                ),
            }
        except WalletError as err:
            LOGGER.error(err)
            return None

    async def from_multikey(self, multikey: str):
        """Fetch a single key."""

        key_info = await self.wallet.get_signing_key(verkey=multikey_to_verkey(multikey))

        return {
            "kid": key_info.kid,
            "multikey": verkey_to_multikey(
                key_info.verkey, alg=key_info.key_type.key_type
            ),
        }

    async def create(self, seed: str = None, kid: str = None, alg: str = DEFAULT_ALG):
        """Create a new key pair."""

        if alg not in ALG_MAPPINGS:
            raise MultikeyManagerError(
                f"Unknown key algorithm, use one of {list(ALG_MAPPINGS.keys())}."
            )

        if kid and await self.kid_exists(kid=kid):
            raise MultikeyManagerError(f"kid '{kid}' already exists in wallet.")

        key_type = ALG_MAPPINGS[alg]["key_type"]
        key_info = await self.wallet.create_key(key_type=key_type, seed=seed, kid=kid)

        return {
            "kid": key_info.kid,
            "multikey": verkey_to_multikey(key_info.verkey, alg=alg),
        }

    async def update(self, multikey: str, kid: str, unbind=False):
        """Bind or unbind a kid with a key pair."""
        (
            await self.unbind_key_id(multikey, kid)
            if unbind
            else await self.bind_key_id(multikey, kid)
        )

        return {"kid": kid, "multikey": multikey}

    async def bind_key_id(self, multikey: str, kid: str):
        """Bind a new key id to a key pair."""
        try:
            return await self.wallet.assign_kid_to_key(multikey_to_verkey(multikey), kid)
        except WalletError as err:
            LOGGER.error(err)
            raise MultikeyManagerError(err)

    async def unbind_key_id(self, multikey: str, kid: str):
        """Unbind a key id from a key pair."""
        try:
            return await self.wallet.unassign_kid_from_key(
                multikey_to_verkey(multikey), kid
            )
        except WalletError as err:
            LOGGER.error(err)
            raise MultikeyManagerError(err)
