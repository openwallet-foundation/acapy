"""V2.0 issue-credential base credential format handler."""

from abc import ABC, abstractclassmethod, abstractmethod
import logging

from typing import Mapping, Tuple

from .....core.error import BaseError
from .....core.profile import Profile
from .....messaging.decorators.attach_decorator import AttachDecorator

from ..messages.cred_format import V30CredFormat
from ..messages.cred_proposal import V30CredProposal
from ..messages.cred_offer import V30CredOffer
from ..messages.cred_request import V30CredRequest
from ..messages.cred_issue import V30CredIssue
from ..models.cred_ex_record import V30CredExRecord

LOGGER = logging.getLogger(__name__)

CredFormatAttachment = Tuple[V30CredFormat, AttachDecorator]


class V30CredFormatError(BaseError):
    """Credential format error under issue-credential protocol v2.0."""


class V30CredFormatHandler(ABC):
    """Base credential format handler."""

    format: V30CredFormat.Format = None

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

    @abstractmethod
    def get_format_identifier(self, message_type: str) -> str:
        """Get attachment format identifier for format and message combination.

        Args:
            message_type (str): Message type for which to return the format identifier

        Returns:
            str: Issue credential attachment format identifier

        """

    @abstractmethod
    def get_format_data(self, message_type: str, data: dict) -> CredFormatAttachment:
        """Get credential format and attachment objects for use in cred ex messages."""

    @abstractclassmethod
    def validate_fields(cls, message_type: str, attachment_data: dict) -> None:
        """Validate attachment data for specific message type and format."""

    @abstractmethod
    async def create_proposal(
        self, cred_ex_record: V30CredExRecord, proposal_data: Mapping
    ) -> CredFormatAttachment:
        """Create format specific credential proposal attachment data."""

    @abstractmethod
    async def receive_proposal(
        self, cred_ex_record: V30CredExRecord, cred_proposal_message: V30CredProposal
    ) -> None:
        """Receive format specific credential proposal message."""

    @abstractmethod
    async def create_offer(
        self, cred_proposal_message: V30CredProposal
    ) -> CredFormatAttachment:
        """Create format specific credential offer attachment data."""

    @abstractmethod
    async def receive_offer(
        self, cred_ex_record: V30CredExRecord, cred_offer_message: V30CredOffer
    ) -> None:
        """Receive foramt specific credential offer message."""

    @abstractmethod
    async def create_request(
        self, cred_ex_record: V30CredExRecord, request_data: Mapping = None
    ) -> CredFormatAttachment:
        """Create format specific credential request attachment data."""

    @abstractmethod
    async def receive_request(
        self, cred_ex_record: V30CredExRecord, cred_request_message: V30CredRequest
    ) -> None:
        """Receive format specific credential request message."""

    @abstractmethod
    async def issue_credential(
        self, cred_ex_record: V30CredExRecord, retries: int = 5
    ) -> CredFormatAttachment:
        """Create format specific issue credential attachment data."""

    @abstractmethod
    async def receive_credential(
        self, cred_ex_record: V30CredExRecord, cred_issue_message: V30CredIssue
    ) -> None:
        """Create format specific issue credential message."""

    @abstractmethod
    async def store_credential(
        self, cred_ex_record: V30CredExRecord, cred_id: str = None
    ) -> None:
        """Store format specific credential from issue credential message."""
