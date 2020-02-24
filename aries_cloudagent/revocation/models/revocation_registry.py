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
        reg_def_json: str = None,
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
        self._reg_def_json = reg_def_json

    @classmethod
    def from_definition(
        cls, revoc_reg_def: dict, public_def: bool
    ) -> "RevocationRegistry":
        """Initialize a revocation registry instance from a definition."""
        reg_id = revoc_reg_def["id"]
        tails_location = revoc_reg_def["value"]["tailsLocation"]
        init = {
            "cred_def_id": revoc_reg_def["credDefId"],
            "reg_def_type": revoc_reg_def["revocDefType"],
            "max_creds": revoc_reg_def["value"]["maxCredNum"],
            "tag": revoc_reg_def["tag"],
            "tails_hash": revoc_reg_def["value"]["tailsHash"],
            "reg_def_json": json.dumps(revoc_reg_def),
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

    async def create_tails_reader(self, context: InjectionContext) -> int:
        """Get a handle for the blob_storage file reader."""
        tails_file_path = Path(self.get_receiving_tails_local_path(context))

        if not tails_file_path.exists():
            raise FileNotFoundError("Tail file does not exist.")

        tails_reader_config = json.dumps(
            {
                "base_dir": str(tails_file_path.parent.absolute()),
                "file": str(tails_file_path.name),
            }
        )
        return await indy.blob_storage.open_reader("default", tails_reader_config)

    def get_receiving_tails_local_path(self, context: InjectionContext):
        """Make the local path to the tail file we download from remote URI."""
        if self._tails_local_path:
            return self._tails_local_path

        tails_file_dir = context.settings.get(
            "holder.revocation.tails_files.path", "/tmp/indy/revocation/tails_files"
        )
        return f"{tails_file_dir}/{self._tails_hash}"

    def has_local_tails_file(self, context: InjectionContext) -> bool:
        """Test if the tails file exists locally."""
        tails_file_path = Path(self.get_receiving_tails_local_path(context))
        return tails_file_path.is_file()

    async def retrieve_tails(self, context: InjectionContext):
        """Fetch the tails file from the public URI."""
        if not self._tails_public_uri:
            raise RevocationError("Tail file public uri is empty")

        try:
            tails_stream = await fetch_stream(self._tails_public_uri)
        except FetchError as e:
            raise RevocationError("Error retrieving tails file") from e

        tails_file_path = Path(self.get_receiving_tails_local_path(context))
        tails_file_dir = tails_file_path.parent
        if not tails_file_dir.exists():
            tails_file_dir.mkdir(parents=True)

        buffer_size = 65536  # should be multiple of 32 bytes for sha256
        with open(tails_file_path, "wb", buffer_size) as tails_file:
            file_hasher = hashlib.sha256()
            buf = await tails_stream.read(buffer_size)
            while len(buf) > 0:
                file_hasher.update(buf)
                tails_file.write(buf)
                buf = await tails_stream.read(buffer_size)

            download_tails_hash = base58.b58encode(file_hasher.digest()).decode("utf-8")
            if download_tails_hash != self.tails_hash:
                raise RevocationError(
                    "The hash of the downloaded tails file does not match."
                )

        self.tails_local_path = tails_file_path
        return self.tails_local_path

    async def create_revocation_state(
        self,
        context: InjectionContext,
        cred_rev_id: str,
        rev_reg_delta: dict,
        timestamp: int,
    ):
        """
        Get credentials stored in the wallet.

        Args:
            cred_rev_id: credential revocation id in revocation registry
            rev_reg_delta: revocation delta
            timestamp: delta timestamp

        :param context:
        :return revocation state
        """

        tails_file_reader = await self.create_tails_reader(context)
        rev_state = await indy.anoncreds.create_revocation_state(
            tails_file_reader,
            rev_reg_def_json=self._reg_def_json,
            cred_rev_id=cred_rev_id,
            rev_reg_delta_json=json.dumps(rev_reg_delta),
            timestamp=timestamp,
        )

        return json.loads(rev_state)

    def __repr__(self) -> str:
        """Return a human readable representation of this class."""
        items = ("{}={}".format(k, repr(v)) for k, v in self.__dict__.items())
        return "<{}({})>".format(self.__class__.__name__, ", ".join(items))
