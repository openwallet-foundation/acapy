"""Classes to manage route coordination."""

from typing import Sequence

import logging

from ...config.injection_context import InjectionContext
from ...core.error import BaseError
from ...messaging.responder import BaseResponder

from .messages.mediation_request import MediationRequest
from .messages.mediation_grant import MediationGrant
from .models.route_coordination import RouteCoordinationSchema, RouteCoordination
from .models.routing_key import RoutingKey


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
    ) -> RouteCoordinationSchema:
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
                recipient_terms=recipient_terms,
                mediator_terms=mediator_terms
            )
        request = await self.create_mediation_request_message(
            recipient_terms=recipient_terms,
            mediator_terms=mediator_terms
        )
        route_coordination.thread_id = request._thread_id
        await route_coordination.save(
                self.context, reason="New mediation initiation request received"
            )

        responder: BaseResponder = await self._context.inject(
                BaseResponder, required=False
            )
        if responder:
            await responder.send(request, connection_id=connection_id)
        return route_coordination

    async def create_mediation_request_message(
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
            mediator_terms=mediation_request.recipient_terms,
            recipient_terms=mediation_request.recipient_terms
        )
        route_coordination_record = await route_coordination.save(self.context)

        return route_coordination_record

    async def create_grant_message(
        self,
        endpoint: str,
        routing_keys: Sequence[str],
    ) -> MediationGrant:
        """
        Create a new mediation grant response.

        Args:
            endpoint: Artificial endpoint for the mediation request
            keys: Assigned keys for mediation

        Returns:
            A new `MediationGrant` message to send to the other agent

        """
        request = MediationGrant(
            endpoint=endpoint,
            routing_keys=routing_keys,
        )
        return request

    async def create_accept_response(
        self,
        route_coordination: RouteCoordination
    ) -> (MediationGrant, RouteCoordination):
        """
        Create a mediator grant response.

        Args:
            route_coordination: Route coordination object

        Returns:
            grant_response: Response message for grant

        """
        async def get_routing_endpoint():
            return "test_endpoint"

        if not route_coordination.state == RouteCoordination.STATE_MEDIATION_RECEIVED:
            raise RouteCoordinationManagerError(
                "Route coordination record not in response state"
            )

        routing_endpoint = await get_routing_endpoint()
        route_coordination.routing_endpoint = routing_endpoint
        route_coordination.state = RouteCoordination.STATE_MEDIATION_GRANTED

        await route_coordination.save(self.context)
        grant_response = await self.create_grant_message(
            endpoint=routing_endpoint,
            routing_keys=[]
        )
        grant_response._thread = {
            "thid": route_coordination.thread_id
        }
        return grant_response, route_coordination

    async def save_routing_key(
        self,
        route_coordination_id: str,
        routing_key: str
    ):
        """
        Saves routing key for specific routing.

        Args:
            route_coordination_id: Route coordination record identifier
            routing_key: Related routin key

        """
        routing_key_record = RoutingKey(
            route_coordination_id = route_coordination_id,
            routing_key = routing_key
        )
        await routing_key.save(self.context)

    async def receive_mediation_grant(
        self
    ):
        """
        Receives mediator grant response.

        """
        connection_id = self.context.connection_record.connection_id

        mediation_grant_message: MediationGrant = self.context.message

        route_coordination = await RouteCoordination.retrieve_by_thread(
            context=self.context,
            thread_id=mediation_grant_message._thread_id
        )
        route_coordination.state = RouteCoordination.STATE_MEDIATION_GRANTED
        route_coordination.routing_endpoint = mediation_grant_message.endpoint

        if mediation_grant_message.routing_keys:
            route_coordination.routing_keys = mediation_grant_message.routing_keys
            for routing_key in mediation_grant_message.routing_keys:
                await self.save_routing_key(
                    route_coordination_id = route_coordination.route_coordination_id,
                    routing_key = routing_key
                )

        await route_coordination.save(self.context)