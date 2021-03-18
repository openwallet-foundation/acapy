"""V2.0 issue-credential base credential format handler."""

from abc import ABC, abstractclassmethod, abstractmethod
import logging

from typing import Mapping, Tuple, Union

from .....core.error import BaseError
from .....core.profile import Profile
from .....messaging.decorators.attach_decorator import AttachDecorator
from .....storage.error import StorageNotFoundError

from ..message_types import ATTACHMENT_FORMAT
from ..messages.cred_format import V20CredFormat
from ..messages.cred_offer import V20CredOffer
from ..messages.cred_request import V20CredRequest
from ..models.detail.indy import V20CredExRecordIndy
from ..models.detail.ld_proof import V20CredExRecordLDProof
from ..models.cred_ex_record import V20CredExRecord

LOGGER = logging.getLogger(__name__)


class V20CredFormatError(BaseError):
    """Credential format error under issue-credential protocol v2.0."""


class V20CredFormatHandler(ABC):
    """Base credential format handler."""

    format: V20CredFormat.Format = None

    def __init__(self, profile: Profile):
        """Initialize CredFormatHandler."""
        super().__init__()

        self._profile = profile

    @property
    def profile(self) -> Profile:
        """
        Accessor for the current profile instance.

        Returns:
            The profile instance for this credential format

        """
        return self._profile

    async def get_detail_record(
        self, cred_ex_id: str
    ) -> Union[V20CredExRecordIndy, V20CredExRecordLDProof]:
        """Retrieve credential exchange detail record by cred_ex_id."""

        async with self.profile.session() as session:
            try:
                return await self.format.detail.retrieve_by_cred_ex_id(
                    session, cred_ex_id
                )
            except StorageNotFoundError:
                return None

    def get_format_identifier(self, message_type: str) -> str:
        """Get attachment format identifier for format and message combination.

        Args:
            message_type (str): Message type for which to return the format identifier

        Returns:
            str: Issue credential attachment format identifier
        """
        return ATTACHMENT_FORMAT[message_type][self.format.api]

    def get_format_data(
        self, message_type: str, data: dict
    ) -> Tuple[V20CredFormat, AttachDecorator]:
        """Get credential format and attachment objects for use in cred ex messages.

        Returns a tuple of both credential format and attachment decorator for use
        in credential exchange messages. It looks up the correct format identifier and
        encodes the data as a base64 attachment.

        Args:
            message_type (str): The message type for which to return the cred format.
                Should be one of the message types defined in the message types file
            data (dict): The data to include in the attach decorator

        Returns:
            Tuple[V20CredFormat, AttachDecorator]: Credential format and
                attachment data objects
        """
        return (
            V20CredFormat(
                attach_id=self.format.api,
                format_=self.get_format_identifier(message_type),
            ),
            AttachDecorator.data_base64(data, ident=self.format.api),
        )

    @abstractclassmethod
    def validate_filter(cls, data: Mapping):
        pass

    @abstractmethod
    async def create_proposal(
        self, cred_ex_record: V20CredExRecord, filter: Mapping = None
    ) -> Tuple[V20CredFormat, AttachDecorator]:
        pass

    @abstractmethod
    async def create_offer(
        self, cred_ex_record: V20CredExRecord
    ) -> Tuple[V20CredFormat, AttachDecorator]:
        pass

    @abstractmethod
    async def receive_offer(
        self, cred_ex_record: V20CredExRecord, cred_offer_message: V20CredOffer
    ):
        pass

    @abstractmethod
    async def create_request(
        self, cred_ex_record: V20CredExRecord, holder_did: str = None
    ):
        pass

    async def receive_request(
        self, cred_ex_record: V20CredExRecord, cred_request_message: V20CredRequest
    ):
        """Format specific handler for receiving credential request message"""

    @abstractmethod
    async def issue_credential(self, cred_ex_record: V20CredExRecord, retries: int = 5):
        pass

    @abstractmethod
    async def store_credential(self, cred_ex_record: V20CredExRecord, cred_id: str):
        pass
