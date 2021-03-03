"""V2.0 indy issue-credential cred format."""

from abc import ABC, abstractclassmethod, abstractmethod
import logging

from typing import Mapping, Tuple, Union

from .....core.error import BaseError
from .....core.profile import Profile
from .....messaging.decorators.attach_decorator import AttachDecorator
from .....storage.error import StorageNotFoundError

from ..messages.cred_format import V20CredFormat
from ..messages.cred_proposal import V20CredProposal
from ..messages.cred_offer import V20CredOffer
from ..models.detail.indy import V20CredExRecordIndy
from ..models.detail.dif import V20CredExRecordDIF
from ..models.cred_ex_record import V20CredExRecord

LOGGER = logging.getLogger(__name__)


class V20CredFormatError(BaseError):
    """Credential format error under issue-credential protocol v2.0."""


class V20CredFormatHandler(ABC):
    "Base credential format handler."

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
    ) -> Union[V20CredExRecordIndy, V20CredExRecordDIF]:
        """Retrieve credential exchange detail record by cred_ex_id."""

        async with self.profile.session() as session:
            try:
                return await self.format.detail.retrieve_by_cred_ex_id(
                    session, cred_ex_id
                )
            except StorageNotFoundError:
                return None

    @abstractclassmethod
    def validate_filter(cls, data: Mapping):
        """"""

    @abstractmethod
    async def create_proposal(
        self, filter: Mapping[str, str]
    ) -> Tuple[V20CredFormat, AttachDecorator]:
        """"""

    @abstractmethod
    async def receive_offer(
        self, cred_ex_record: V20CredExRecord, cred_offer_message: V20CredOffer
    ):
        """"""

    @abstractmethod
    async def create_offer(
        self, cred_proposal_message: V20CredProposal
    ) -> Tuple[V20CredFormat, AttachDecorator]:
        """"""

    @abstractmethod
    async def create_request(
        self,
        cred_ex_record: V20CredExRecord,
        holder_did: str,
    ):
        """"""

    @abstractmethod
    async def issue_credential(self, cred_ex_record: V20CredExRecord, retries: int = 5):
        """"""

    @abstractmethod
    async def store_credential(self, cred_ex_record: V20CredExRecord, cred_id: str):
        """"""