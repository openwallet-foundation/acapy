"""Classes for managing a revocation registry."""

import json
import tempfile

import indy.blob_storage

from ...utils.http import fetch, FetchError
from ...utils.temp import get_temp_dir

from ..error import RevocationError


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
            "reg_def_type": revoc_reg_def["regDefType"],
            "max_creds": revoc_reg_def["value"]["maxCredNum"],
            "tag": revoc_reg_def["tag"],
            "tails_hash": revoc_reg_def["value"]["tailsHash"],
        }
        if public_def:
            init["tails_local_path"] = tails_location
        else:
            init["tails_public_uri"] = tails_location
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
        if self._tails_local_path:
            tails_reader_config = json.dumps(
                {"base_dir": self.get_temp_dir(), "file": self._tails_local_path}
            )
            return await indy.blob_storage.open_reader("default", tails_reader_config)

    async def retrieve_tails(self, target_dir: str) -> str:
        """Fetch the tails file from the public URI."""
        if self._tails_public_uri:
            try:
                tails = await fetch(self._tails_public_uri)
            except FetchError as e:
                raise RevocationError("Error retrieving tails file") from e
            with tempfile.mkstemp(suffix="tails", dir=target_dir, text=True) as tf:
                tf.write(tails)
                return tf.name

    def __repr__(self) -> str:
        """Return a human readable representation of this class."""
        items = ("{}={}".format(k, repr(v)) for k, v in self.__dict__.items())
        return "<{}({})>".format(self.__class__.__name__, ", ".join(items))
