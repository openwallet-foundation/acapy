from typing import List, Optional, Sequence, Tuple, Union, cast
from ..base import BaseWallet
from ..util import b58_to_bytes, bytes_to_b58
from aries_askar import Key


class AskarWallet(BaseWallet):
    """Aries-Askar wallet implementation."""

    async def get_local_keys(self):
        """Get list of defined local DIDs.

        Returns:
            A list of locally stored DIDs as `DIDInfo` instances

        """
        key_entries = await self._session.handle.fetch_all_keys(
            # tag_filter={"kid": kid}, limit=2
        )
        entry = key_entries[0]
        key = cast(Key, entry.key)
        verkey = bytes_to_b58(key.get_public_bytes())
        return verkey

    async def get_local_key(self, kid: str):
        """Get list of defined local DIDs.

        Returns:
            A list of locally stored DIDs as `DIDInfo` instances

        """
        key_entries = await self._session.handle.fetch_all_keys(
            tag_filter={"kid": kid}, limit=2
        )
        entry = key_entries[0]
        key = cast(Key, entry.key)
        verkey = bytes_to_b58(key.get_public_bytes())
        return verkey
