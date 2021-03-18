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
from ..messages.cred_proposal import V20CredProposal
from ..messages.cred_offer import V20CredOffer
from ..messages.cred_request import V20CredRequest
from ..messages.cred_issue import V20CredIssue
from ..models.detail.indy import V20CredExRecordIndy
from ..models.detail.ld_proof import V20CredExRecordLDProof
from ..models.cred_ex_record import V20CredExRecord

LOGGER = logging.getLogger(__name__)

CredFormatAttachment = Tuple[V20CredFormat, AttachDecorator]


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

    def get_format_data(self, message_type: str, data: dict) -> CredFormatAttachment:
        """Get credential format and attachment objects for use in cred ex messages.

        Returns a tuple of both credential format and attachment decorator for use
        in credential exchange messages. It looks up the correct format identifier and
        encodes the data as a base64 attachment.

        Args:
            message_type (str): The message type for which to return the cred format.
                Should be one of the message types defined in the message types file
            data (dict): The data to include in the attach decorator

        Returns:
            CredFormatAttachment: Credential format and attachment data objects
        """
        return (
            V20CredFormat(
                attach_id=self.format.api,
                format_=self.get_format_identifier(message_type),
            ),
            AttachDecorator.data_base64(data, ident=self.format.api),
        )

    @abstractclassmethod
    def validate_fields(cls, message_type: str, attachment_data: dict) -> None:
        """Validate attachment data for specific message type and format"""

    @abstractmethod
    async def create_proposal(
        self, cred_ex_record: V20CredExRecord, proposal_data: Mapping
    ) -> CredFormatAttachment:
        """Format specific handler for creating credential proposal attachment format data"""

    @abstractmethod
    async def receive_proposal(
        self, cred_ex_record: V20CredExRecord, cred_proposal_message: V20CredProposal
    ) -> None:
        """Format specific handler for receiving credential proposal message"""

    @abstractmethod
    async def create_offer(
        self, cred_ex_record: V20CredExRecord, offer_data: Mapping = None
    ) -> CredFormatAttachment:
        """Format specific handler for creating credential offer attachment format data"""

    @abstractmethod
    async def receive_offer(
        self, cred_ex_record: V20CredExRecord, cred_offer_message: V20CredOffer
    ) -> None:
        """Format specific handler for receiving credential offer message"""

    @abstractmethod
    async def create_request(
        self, cred_ex_record: V20CredExRecord, request_data: Mapping = None
    ) -> CredFormatAttachment:
        """Format specific handler for creating credential request attachment format data"""

    @abstractmethod
    async def receive_request(
        self, cred_ex_record: V20CredExRecord, cred_request_message: V20CredRequest
    ) -> None:
        """Format specific handler for receiving credential request message"""

    @abstractmethod
    # TODO: add issue_data or is this never needed?
    async def issue_credential(
        self, cred_ex_record: V20CredExRecord, retries: int = 5
    ) -> CredFormatAttachment:
        """Format specific handler for creating issue credential attachment format data"""

    @abstractmethod
    async def receive_credential(
        self, cred_ex_record: V20CredExRecord, cred_issue_message: V20CredIssue
    ) -> None:
        """Format specific handler for receiving issue credential message"""

    @abstractmethod
    async def store_credential(
        self, cred_ex_record: V20CredExRecord, cred_id: str = None
    ) -> None:
        """Format specific handler for storing credential from issue credential message"""
