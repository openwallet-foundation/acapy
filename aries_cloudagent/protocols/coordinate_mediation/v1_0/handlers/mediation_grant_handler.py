"""Handler for mediate-grant message."""

from .....messaging.base_handler import BaseHandler, HandlerException
from .....messaging.request_context import RequestContext
from .....messaging.responder import BaseResponder
from .....multitenant.base import BaseMultitenantManager
from .....storage.error import StorageNotFoundError

from ..manager import MediationManager
from ..messages.mediate_grant import MediationGrant
from ..models.mediation_record import MediationRecord


class MediationGrantHandler(BaseHandler):
    """Handler for mediate-grant message."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Handle mediate-grant message."""
        self._logger.debug(
            "%s called with context %s", self.__class__.__name__, context
        )
        assert isinstance(context.message, MediationGrant)

        if not context.connection_ready:
            raise HandlerException("Received mediation grant from inactive connection")

        profile = context.profile
        mgr = MediationManager(profile)
        try:
            async with profile.session() as session:
                record = await MediationRecord.retrieve_by_connection_id(
                    session, context.connection_record.connection_id
                )
            await mgr.request_granted(record, context.message)

            # Multitenancy setup
            multitenant_mgr = profile.inject_or(BaseMultitenantManager)
            wallet_id = profile.settings.get("wallet.id")

            if multitenant_mgr and wallet_id:
                base_mediation_record = await multitenant_mgr.get_default_mediator()

                # If we have a base mediator and sub wallet mediator
                # we need to register the base mediator routing key at the
                # sub wallet mediator
                if base_mediation_record:
                    # Last routing key needs to be registered at the mediator
                    keylist_updates = await mgr.add_key(
                        base_mediation_record.routing_keys[-1]
                    )

                    await responder.send(
                        keylist_updates,
                        connection_id=context.connection_record.connection_id,
                    )

            # Set to default if metadata set on connection to do so
            async with profile.session() as session:
                mediationRecord = await context.connection_record.metadata_get(
                    session, MediationManager.SET_TO_DEFAULT_ON_GRANTED
                )

            if mediationRecord:
                await mgr.set_default_mediator(record)

        except StorageNotFoundError as err:
            raise HandlerException(
                "Received mediation grant from connection from which mediation "
                "has not been requested."
            ) from err
