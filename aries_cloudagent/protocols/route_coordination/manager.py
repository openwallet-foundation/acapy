"""Classes to manage route coordination."""

from typing import Sequence

import logging

from ...config.injection_context import InjectionContext
from ...core.error import BaseError
from ...messaging.responder import BaseResponder

from .messages.mediation_request import MediationRequest
from .models.route_coordination import RouteCoordinationSchema, RouteCoordination
from .models.routing_term import RoutingTerm


class RouteCoordinationManagerError(BaseError):
    """Route error."""


class RouteCoordinationManager:
    """Class for managing connections."""

    RECORD_TYPE_DID_DOC = "did_doc"
    RECORD_TYPE_DID_KEY = "did_key"

    def __init__(self, context: InjectionContext):
        """
        Initialize a RouteCoordinationManager.

        Args:
            context: The context for this route coordination manager
        """
        self._context = context
        self._logger = logging.getLogger(__name__)

    @property
    def context(self) -> InjectionContext:
        """
        Accessor for the current injection context.

        Returns:
            The injection context for this route coordination manager

        """
        return self._context

    async def create_mediation_request(
        self,
        connection_id: str,
        recipient_terms: Sequence[str],
        mediator_terms: Sequence[str]
    ) -> (RouteCoordinationSchema, Sequence[RoutingTerm], Sequence[RoutingTerm]):
        """
        Create a mediator request.

        Args:
            connection_id: Connection ID for mediation request
            recipient_terms: Recipient terms for mediation
            recipient_terms: Agreed mediator terms for mediation

        Returns:
            mediation_route: New mediation route record

        """
        route_coordination = RouteCoordination(
                connection_id=connection_id,
                state=RouteCoordination.STATE_MEDIATION_REQUEST,
                initiator=RouteCoordination.INITIATOR_SELF,
                role=RouteCoordination.ROLE_RECIPIENT,
            )
        await route_coordination.save(
                self.context, reason="New mediation initiation request received"
            )
        recipient_routing_terms = []
        if recipient_terms:
            for recipient_term in recipient_terms:
                routing_term = RoutingTerm(
                    route_coordination_id=route_coordination.route_coordination_id,
                    owner=RoutingTerm.OWNER_RECIPIENT,
                    term=recipient_term)
                await routing_term.save(
                    self.context, reason="New mediation initiation request received"
                )
                recipient_routing_terms.append(routing_term)

        mediator_routing_terms = []
        if recipient_terms:
            for mediator_term in mediator_terms:
                routing_term = RoutingTerm(
                    route_coordination_id=route_coordination.route_coordination_id,
                    owner=RoutingTerm.OWNER_MEDIATOR,
                    term=mediator_term)
                await routing_term.save(
                    self.context, reason="New mediation initiation request received"
                )
                mediator_routing_terms.append(routing_term)

        request = await self.create_request(
            recipient_terms=recipient_terms,
            mediator_terms=mediator_routing_terms
        )
        responder: BaseResponder = await self._context.inject(
                BaseResponder, required=False
            )
        if responder:
            await responder.send(request, connection_id=connection_id)
        return route_coordination, recipient_routing_terms, mediator_routing_terms

    async def create_request(
        self,
        recipient_terms: Sequence[str],
        mediator_terms: Sequence[str],
    ) -> MediationRequest:
        """
        Create a new mediation request.

        Args:
            recipient_terms: Terms that recipient wants to mediator to agree to
            recipient_terms: Terms that recipient accepted for mediator

        Returns:
            A new `MediationRequest` message to send to the other agent

        """
        request = MediationRequest(
            mediator_terms=mediator_terms,
            recipient_terms=recipient_terms,
        )
        return request

    async def receive_request(
        self
    ) -> RouteCoordination:
        """
        Receive a mediation request.

        Returns:
            A tuple route coordination

        """
        connection_id = self.context.connection_record.connection_id

        mediation_request: MediationRequest = self.context.message
        route_coordination = RouteCoordination(
            connection_id=connection_id,
            thread_id=mediation_request._thread_id,
            initiator=RouteCoordination.INITIATOR_EXTERNAL,
            role=RouteCoordination.ROLE_MEDIATOR,
            state=RouteCoordination.STATE_MEDIATION_RECEIVED,
        )
        route_coordination_record = await route_coordination.save(self.context)

        if mediation_request.recipient_terms:
            for recipient_term in mediation_request.recipient_terms:
                routing_term = RoutingTerm(
                    route_coordination_id=route_coordination.route_coordination_id,
                    owner=RoutingTerm.OWNER_RECIPIENT,
                    term=recipient_term)
                await routing_term.save(
                    self.context, reason="New mediation initiation request received"
                )

        if mediation_request.recipient_terms:
            for mediator_term in mediation_request.mediator_terms:
                routing_term = RoutingTerm(
                    route_coordination_id=route_coordination.route_coordination_id,
                    owner=RoutingTerm.OWNER_MEDIATOR,
                    term=mediator_term)
                await routing_term.save(
                    self.context, reason="New mediation initiation request received"
                )
        return route_coordination_record
