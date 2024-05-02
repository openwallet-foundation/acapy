"""Automated setup process for AnonCreds credential definitions with revocation."""

import logging
from abc import ABC, abstractmethod

from aries_cloudagent.protocols.endorse_transaction.v1_0.util import is_author_role

from ..anoncreds.revocation import AnonCredsRevocation
from ..core.event_bus import EventBus
from ..core.profile import Profile
from ..revocation.util import notify_revocation_published_event
from .events import (
    CRED_DEF_FINISHED_PATTERN,
    REV_LIST_FINISHED_PATTERN,
    REV_REG_DEF_FINISHED_PATTERN,
    CredDefFinishedEvent,
    RevListFinishedEvent,
    RevRegDefFinishedEvent,
)

LOGGER = logging.getLogger(__name__)


class AnonCredsRevocationSetupManager(ABC):
    """Base class for automated setup of revocation."""

    @abstractmethod
    def register_events(self, event_bus: EventBus):
        """Event registration."""


class DefaultRevocationSetup(AnonCredsRevocationSetupManager):
    """Manager for automated setup of revocation support.

    This manager models a state machine for the revocation setup process where
    the transitions are triggered by the `finished` event of the previous
    artifact. The state machine is as follows:

    [*] --> Cred Def
    Cred Def --> Rev Reg Def
    Rev Reg Def --> Rev List
    Rev List --> [*]

    This implementation of an AnonCredsRevocationSetupManager will create two
    revocation registries for each credential definition supporting revocation;
    one that is active and one that is pending. When the active registry fills,
    the pending registry will be activated and a new pending registry will be
    created. This will continue indefinitely.

    This hot-swap approach to revocation registry management allows for
    issuance operations to be performed without a delay for registry
    creation.
    """

    REGISTRY_TYPE = "CL_ACCUM"
    INITIAL_REGISTRY_COUNT = 2

    def __init__(self):
        """Init manager."""

    def register_events(self, event_bus: EventBus):
        """Register event listeners."""
        event_bus.subscribe(CRED_DEF_FINISHED_PATTERN, self.on_cred_def)
        event_bus.subscribe(REV_REG_DEF_FINISHED_PATTERN, self.on_rev_reg_def)
        event_bus.subscribe(REV_LIST_FINISHED_PATTERN, self.on_rev_list)

    async def on_cred_def(self, profile: Profile, event: CredDefFinishedEvent):
        """Handle cred def finished."""
        payload = event.payload
        auto_create_revocation = is_author_role(profile) and profile.settings.get(
            "endorser.auto_create_rev_reg", False
        )

        if payload.support_revocation or auto_create_revocation:
            revoc = AnonCredsRevocation(profile)
            for registry_count in range(self.INITIAL_REGISTRY_COUNT):
                await revoc.create_and_register_revocation_registry_definition(
                    issuer_id=payload.issuer_id,
                    cred_def_id=payload.cred_def_id,
                    registry_type=self.REGISTRY_TYPE,
                    max_cred_num=payload.max_cred_num,
                    tag=str(registry_count),
                    options=payload.options,
                )

    async def on_rev_reg_def(self, profile: Profile, event: RevRegDefFinishedEvent):
        """Handle rev reg def finished."""
        payload = event.payload

        auto_create_revocation = True
        if is_author_role(profile):
            auto_create_revocation = profile.settings.get(
                "endorser.auto_create_rev_reg", False
            )

        if auto_create_revocation:
            revoc = AnonCredsRevocation(profile)
            await revoc.upload_tails_file(payload.rev_reg_def)
            await revoc.create_and_register_revocation_list(
                payload.rev_reg_def_id, payload.options
            )

            if payload.rev_reg_def.tag == str(0):
                # Mark the first registry as active
                await revoc.set_active_registry(payload.rev_reg_def_id)

    async def on_rev_list(self, profile: Profile, event: RevListFinishedEvent):
        """Handle rev list finished."""
        await notify_revocation_published_event(
            profile, event.payload.rev_reg_id, event.payload.revoked
        )
