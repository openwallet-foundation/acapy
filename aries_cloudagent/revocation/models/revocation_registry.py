"""Classes for managing a revocation registry."""

import json
from pathlib import Path

import indy.blob_storage

from ...config.injection_context import InjectionContext
from ...utils.http import FetchError, fetch_stream
from ...utils.temp import get_temp_dir

from ..error import RevocationError
import hashlib
import base58


class RevocationRegistry:
    """Manage a revocation registry and tails file."""

    def __init__(
        self,
        registry_id: str = None,
        *,
        cred_def_id: str = None,
        issuer_did: str = None,
        max_creds: int = None,
        reg_def_type: str = None,
        tag: str = None,
        tails_local_path: str = None,
        tails_public_uri: str = None,
        tails_hash: str = None,
    ):
        """Initialize the revocation registry instance."""
        self._cred_def_id = cred_def_id
        self._issuer_did = issuer_did
        self._max_creds = max_creds
        self._reg_def_type = reg_def_type
        self._registry_id = registry_id
        self._tag = tag
        self._tails_local_path = tails_local_path
        self._tails_public_uri = tails_public_uri
        self._tails_hash = tails_hash

    @classmethod
    def from_definition(
        cls, revoc_reg_def: dict, public_def: bool
    ) -> "RevocationRegistry":
        """Initialize a revocation registry instance from a definition."""
        reg_id = revoc_reg_def.get("id")
        tails_location = revoc_reg_def["value"]["tailsLocation"]
        init = {
            "cred_def_id": revoc_reg_def["credDefId"],
            "reg_def_type": revoc_reg_def["revocDefType"],
            "max_creds": revoc_reg_def["value"]["maxCredNum"],
            "tag": revoc_reg_def["tag"],
            "tails_hash": revoc_reg_def["value"]["tailsHash"],
        }
        if public_def:
            init["tails_public_uri"] = tails_location
        else:
            init["tails_local_path"] = tails_location

        # currently ignored - definition version, public keys
        return cls(reg_id, **init)

    @classmethod
    def get_temp_dir(cls) -> str:
        """Accessor for the temp directory."""
        return get_temp_dir("revoc")

    @property
    def cred_def_id(self) -> str:
        """Accessor for the credential definition ID."""
        return self._cred_def_id

    @property
    def issuer_did(self) -> str:
        """Accessor for the issuer DID."""
        return self._issuer_did

    @property
    def max_creds(self) -> int:
        """Accessor for the maximum number of issued credentials."""
        return self._max_creds

    @property
    def reg_def_type(self) -> str:
        """Accessor for the revocation registry type."""
        return self._reg_def_type

    @property
    def registry_id(self) -> str:
        """Accessor for the revocation registry ID."""
        return self._registry_id

    @property
    def tag(self) -> str:
        """Accessor for the tag part of the revoc. reg. ID."""
        return self._tag

    @property
    def tails_hash(self) -> str:
        """Accessor for the tails file hash."""
        return self._tails_hash

    @property
    def tails_local_path(self) -> str:
        """Accessor for the tails file local path."""
        return self._tails_local_path

    @tails_local_path.setter
    def tails_local_path(self, new_path: str):
        """Setter for the tails file local path."""
        self._tails_local_path = new_path

    @property
    def tails_public_uri(self) -> str:
        """Accessor for the tails file public URI."""
        return self._tails_public_uri

    @tails_public_uri.setter
    def tails_public_uri(self, new_uri: str):
        """Setter for the tails file public URI."""
        self._tails_public_uri = new_uri

    async def create_tails_reader(self) -> int:
        """Get a handle for the blob_storage file reader."""
        if not self.has_local_tail_file():
            raise RevocationError("Tail file does not exist or not valid.")

        if self._tails_local_path:
            tails_reader_config = json.dumps(
                {"base_dir": self.get_temp_dir(), "file": self._tails_local_path}
            )
            return await indy.blob_storage.open_reader("default", tails_reader_config)

    def get_receiving_tails_local_path(self, context: InjectionContext):
        """Make the local path to the tail file we download from remote URI"""
        tail_file_dir = context.settings.get("holder.revocation.tail_files.path", "/tmp/indy/revocation/tail_files")
        return f"{tail_file_dir}/{self.registry_id}"

    def has_local_tail_file(self) -> bool:
        if not self._tails_local_path:
            return False

        tail_file_path = Path(self._tails_local_path)
        if not tail_file_path.is_file():
            return False

        return True

    async def retrieve_tails(self, context: InjectionContext):
        """Fetch the tails file from the public URI."""
        if not self._tails_public_uri:
            raise RevocationError("Tail file public uri is empty")

        try:
            tails_stream = await fetch_stream(self._tails_public_uri)
        except FetchError as e:
            raise RevocationError("Error retrieving tails file") from e

        tails_file_path = Path(self.get_receiving_tails_local_path(context))
        tails_file_dir =  tails_file_path.parent
        if not tails_file_dir.exists():
            tails_file_dir.mkdir(parents=True)

        buffer_size = 65536 # should be multiple of 32 bytes for sha256
        with open(tails_file_path, "wb", buffer_size) as tail_file:
            file_hasher = hashlib.sha256()
            buf = await tails_stream.read(buffer_size)
            while len(buf) > 0:
                file_hasher.update(buf)
                tail_file.write(buf)
                buf = await tails_stream.read(buffer_size)

            download_tail_hash = base58.b58encode(file_hasher.digest()).decode("utf-8")
            if download_tail_hash != self.tails_hash:
                raise RevocationError("The hash of the downloaded tails file does not match.")

        self.tails_local_path = tails_file_path
        return self.tails_local_path

    def __repr__(self) -> str:
        """Return a human readable representation of this class."""
        items = ("{}={}".format(k, repr(v)) for k, v in self.__dict__.items())
        return "<{}({})>".format(self.__class__.__name__, ", ".join(items))
