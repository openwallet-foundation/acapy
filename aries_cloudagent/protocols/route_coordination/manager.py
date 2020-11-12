"""Classes to manage route coordination."""

from typing import Sequence

import logging

from ...config.injection_context import InjectionContext
from ...core.error import BaseError
from ...messaging.responder import BaseResponder

from .messages.mediation_request import MediationRequest
from .messages.mediation_grant import MediationGrant
from .messages.mediation_deny import MediationDeny
from .messages.keylist_update_request import KeylistUpdateRequest
from .messages.keylist_update_response import KeylistUpdateResponse
from .messages.inner.keylist_update_rule import KeylistUpdateRule
from .messages.inner.keylist_update_result import KeylistUpdateResult
from .messages.keylist_query import KeylistQuery
from .messages.inner.keylist_query_paginate import KeylistQueryPaginate
from .messages.keylist import KeylistQueryResponse
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
            mediator_terms=mediation_request.mediator_terms,
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
        grant_response = MediationGrant(
            endpoint=endpoint,
            routing_keys=routing_keys,
        )
        return grant_response

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
            return self.context.settings.get("default_endpoint")

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
        Save routing key for specific routing.

        Args:
            route_coordination_id: Route coordination record identifier
            routing_key: Related routin key

        """

        routing_key_record = RoutingKey(
            route_coordination_id=route_coordination_id,
            routing_key=routing_key
        )
        await routing_key_record.save(self.context)

    async def receive_mediation_grant(
        self
    ):
        """Receives mediator grant response."""

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
                    route_coordination_id=route_coordination.route_coordination_id,
                    routing_key=routing_key
                )

        await route_coordination.save(self.context)
        return route_coordination

    async def create_deny_message(
        self,
        mediator_terms: Sequence[str] = None,
        recipient_terms: Sequence[str] = None
    ) -> MediationDeny:
        """
        Create a new mediation deny response.

        Args:
            mediator_terms: Terms that mediator wants to recipient to agree to
            recipient_terms: Terms that recipient wants to mediator to agree to

        Returns:
            A new `MediationDeny` message to send to the other agent

        """
        response = MediationDeny(
            mediator_terms=mediator_terms,
            recipient_terms=recipient_terms,
        )
        return response

    async def create_deny_response(
        self,
        route_coordination: RouteCoordination,
        mediator_terms: Sequence[str] = None,
        recipient_terms: Sequence[str] = None
    ) -> (MediationDeny, RouteCoordination):
        """
        Create a mediator grant response.

        Args:
            route_coordination: Route coordination object

        Returns:
            grant_response: Response message for grant

        """
        route_coordination.mediator_terms = mediator_terms
        route_coordination.recipient_terms = recipient_terms
        route_coordination.state = RouteCoordination.STATE_MEDIATION_DENIED

        await route_coordination.save(self.context)
        deny_response = await self.create_deny_message(
            mediator_terms=mediator_terms,
            recipient_terms=recipient_terms
        )
        deny_response._thread = {
            "thid": route_coordination.thread_id
        }
        return deny_response, route_coordination

    async def receive_mediation_deny(
        self
    ):
        """Receives mediator deny response."""

        mediation_deny_message: MediationDeny = self.context.message

        route_coordination = await RouteCoordination.retrieve_by_thread(
            context=self.context,
            thread_id=mediation_deny_message._thread_id
        )
        route_coordination.state = RouteCoordination.STATE_MEDIATION_DENIED
        route_coordination.mediator_terms = mediation_deny_message.mediator_terms
        route_coordination.recipient_terms = mediation_deny_message.recipient_terms

        await route_coordination.save(self.context)
        return route_coordination

    async def create_keylist_update_request(
        self,
        updates: Sequence[KeylistUpdateRule]
    ) -> KeylistUpdateRequest:
        """
        Create a new keylist update request.

        Args:
            keylist: Terms that recipient wants to mediator to agree to

        Returns:
            A new `KeylistUpdateRequest` message to send to the other agent

        """
        request = KeylistUpdateRequest(
            updates=updates
        )
        return request

    async def receive_keylist_update_request(
        self
    ):
        """Receives mediator keylist update request."""

        connection_id = self.context.connection_record.connection_id
        keylist_update_request: KeylistUpdateRequest = self.context.message

        route_coordination = await RouteCoordination.retrieve_by_connection_id(
            context=self.context,
            connection_id=connection_id
        )

        if not route_coordination:
            raise RouteCoordinationManagerError(
                "Route coordination for connection couldn't be found"
            )
        updated = []
        for update_record in keylist_update_request.updates:
            operation_result = KeylistUpdateResult(
                recipient_key=update_record.recipient_key,
                action=update_record.action,
            )
            if update_record.action == KeylistUpdateRule.RULE_ADD:
                if update_record.recipient_key in route_coordination.routing_keys:
                    operation_result.result = KeylistUpdateResult.RESULT_NO_CHANGE
                else:
                    routing_key = RoutingKey(
                        routing_key=update_record.recipient_key,
                        route_coordination_id=route_coordination.route_coordination_id
                    )
                    try:
                        await routing_key.save(self.context)
                        route_coordination.routing_keys.append(
                            update_record.recipient_key
                        )
                        operation_result.result = KeylistUpdateResult.RESULT_SUCCESS
                    except BaseException:
                        operation_result.result = \
                            KeylistUpdateResult.RESULT_SERVER_ERROR

            elif update_record.action == KeylistUpdateRule.RULE_REMOVE:
                if update_record.recipient_key not in route_coordination.routing_keys:
                    operation_result.result = KeylistUpdateResult.RESULT_NO_CHANGE
                else:
                    routing_key = await RoutingKey.retrieve_by_routing_key_and_coord_id(
                        context=self.context,
                        routing_key=update_record.recipient_key,
                        route_coordination_id=route_coordination.route_coordination_id
                    )
                    try:
                        await routing_key.delete_record(self.context)
                        route_coordination.routing_keys.remove(
                            update_record.recipient_key
                        )
                        operation_result.result = KeylistUpdateResult.RESULT_SUCCESS
                    except BaseException:
                        operation_result.result = \
                            KeylistUpdateResult.RESULT_SERVER_ERROR

            updated.append(operation_result)

        # FIXME - save for each update?
        await route_coordination.save(self.context)

        response = KeylistUpdateResponse(
            updated=updated
        )

        responder: BaseResponder = await self._context.inject(
                BaseResponder, required=False
            )
        if responder:
            await responder.send(response, connection_id=connection_id)

    async def receive_keylist_update_response(
        self
    ) -> (Sequence[str], Sequence[str]):
        """Receives mediator keylist update response."""

        connection_id = self.context.connection_record.connection_id
        keylist_update_response: KeylistUpdateResponse = self.context.message

        route_coordination = await RouteCoordination.retrieve_by_connection_id(
            context=self.context,
            connection_id=connection_id
        )

        if not route_coordination:
            raise RouteCoordinationManagerError(
                "Route coordination for connection couldn't be found"
            )

        server_error = []
        client_error = []

        for updated_record in keylist_update_response.updated:
            if updated_record.result in (
                KeylistUpdateResult.RESULT_SUCCESS,
                KeylistUpdateResult.RESULT_NO_CHANGE
            ):
                if updated_record.action == KeylistUpdateResult.RULE_ADD:
                    if updated_record.recipient_key not in (
                        route_coordination.routing_keys
                    ):
                        route_coordination.routing_keys.append(
                            updated_record.recipient_key
                            )
                elif updated_record.action == KeylistUpdateResult.RULE_REMOVE:
                    route_coordination.routing_keys.remove(updated_record.recipient_key)
            elif updated_record.result == KeylistUpdateResult.RESULT_SERVER_ERROR:
                server_error.append(updated_record.recipient_key)
            elif updated_record.result == KeylistUpdateResult.RESULT_CLIENT_ERROR:
                client_error.append(updated_record.recipient_key)

        # FIXME - save for each update?
        await route_coordination.save(self.context)
        return (server_error, client_error)

    async def create_keylist_query_request_request(
        self,
        limit: int,
        offset: int,
        filter: dict
    ) -> KeylistQuery:
        """
        Create a new keylist query request.

        Args:
            limit: Total keylist limit for response
            offset: Offset value for keylist query
            filter: Dictionary object for filtering keylist

        Returns:
            A new `KeylistQuery` message to send to the other agent

        """
        request = KeylistQuery(
            filter=filter,
            paginate=KeylistQueryPaginate(
                limit=limit,
                offset=offset
            )
        )
        return request

    def routing_key_sort(self, routing_key):
        """Get the sorting key for a particular routing key list."""
        return routing_key["routing_key"]

    async def receive_keylist_query_request(
        self
    ):
        """Receives mediator keylist update request."""
        def sample_result(result, offset=0, limit=None):
            return result[offset:(limit + offset if limit is not None else None)]

        connection_id = self.context.connection_record.connection_id
        keylist_query: KeylistQuery = self.context.message

        route_coordination = await RouteCoordination.retrieve_by_connection_id(
            context=self.context,
            connection_id=connection_id
        )

        if not route_coordination:
            raise RouteCoordinationManagerError(
                "Route coordination for connection couldn't be found"
            )

        tag_filter = {
            "route_coordination_id": route_coordination.route_coordination_id
        }
        if keylist_query.filter:
            filter_keys = keylist_query.filter.keys()
            if filter_keys:
                for key in filter_keys:
                    if key in (
                        "routing_key"
                    ):
                        filtering_key = [
                            {
                                key: val
                            }
                            for val in keylist_query.filter[key]
                        ]
                        tag_filter["$or"] = filtering_key

        post_filter = {}
        records = await RoutingKey.query(self.context, tag_filter, post_filter)
        records = [rec.serialize() for rec in records]
        records.sort(key=self.routing_key_sort)
        records = sample_result(
            result=records,
            offset=keylist_query.paginate.offset,
            limit=keylist_query.paginate.limit
        )

        response = KeylistQueryResponse(
            keys=[record['routing_key'] for record in records],
            pagination=keylist_query.paginate
        )

        responder: BaseResponder = await self._context.inject(
                BaseResponder, required=False
            )
        if responder:
            await responder.send(response, connection_id=connection_id)
