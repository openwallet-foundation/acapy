"""
The conductor is responsible for coordinating messages that are received
over the network, communicating with the ledger, passing messages to handlers,
and storing data in the wallet.
"""

import json
import logging

from typing import Coroutine, Dict, Union

from .connection import ConnectionManager
from .classloader import ClassLoader
from .dispatcher import Dispatcher
from .error import BaseError
from .logging import LoggingConfigurator
from .messaging.agent_message import AgentMessage
from .messaging.message_factory import MessageFactory
from .messaging.request_context import RequestContext
from .models.connection_target import ConnectionTarget
from .transport.inbound import InboundTransportConfiguration
from .transport.inbound.manager import InboundTransportManager
from .transport.outbound.manager import OutboundTransportManager
from .transport.outbound.queue.basic import BasicOutboundMessageQueue


class ConductorError(BaseError):
    pass

class Conductor:
    STORAGE_TYPES = {
        "basic": "indy_catalyst_agent.storage.basic.BasicStorage",
        "indy": "indy_catalyst_agent.storage.indy.IndyStorage",
    }
    WALLET_TYPES = {
        "basic": "indy_catalyst_agent.wallet.basic.BasicWallet",
        "indy": "indy_catalyst_agent.wallet.indy.IndyWallet",
    }

    def __init__(
        self, transport_configs: InboundTransportConfiguration, outbound_transports,
        message_factory: MessageFactory, settings: dict,
    ) -> None:
        self.context = None
        self.logger = logging.getLogger(__name__)
        self.message_factory = message_factory
        self.inbound_transport_configs = transport_configs
        self.outbound_transports = outbound_transports
        self.settings = settings.copy() if settings else {}

    async def start(self) -> None:
        context = RequestContext()
        context.default_endpoint = self.settings.get("default_endpoint", "http://localhost:10001")
        context.default_label = self.settings.get("default_name", "Indy Catalyst Agent")
        context.message_factory = self.message_factory

        wallet_type = self.settings.get("wallet.type", "basic").lower()
        wallet_type = self.WALLET_TYPES.get(wallet_type, wallet_type)
        wallet_cfg = {}
        if "wallet.key" in self.settings:
            wallet_cfg["key"] = self.settings["wallet.key"]
        if "wallet.name" in self.settings:
            wallet_cfg["name"] = self.settings["wallet.name"]
        context.wallet = ClassLoader.load_class(wallet_type)(wallet_cfg)

        storage_type = self.settings.get("storage.type", "basic").lower()
        storage_type = self.STORAGE_TYPES.get(storage_type, storage_type)
        context.storage = ClassLoader.load_class(storage_type)(context.wallet)

        self.context = context
        self.dispatcher = Dispatcher()

        # Register all inbound transports
        self.inbound_transport_manager = InboundTransportManager()
        for inbound_transport_config in self.inbound_transport_configs:
            module = inbound_transport_config.module
            host = inbound_transport_config.host
            port = inbound_transport_config.port

            self.inbound_transport_manager.register(
                module, host, port, self.inbound_message_router
            )

        await self.inbound_transport_manager.start_all()

        # TODO: Set queue driver dynamically via cli args
        queue = BasicOutboundMessageQueue
        self.outbound_transport_manager = OutboundTransportManager(queue)
        for outbound_transport in self.outbound_transports:
            try:
                self.outbound_transport_manager.register(outbound_transport)
            except Exception:
                self.logger.exception("Unable to register outbound transport")

        await self.outbound_transport_manager.start_all()

        # Show some details about the configuration to the user
        LoggingConfigurator.print_banner(
            self.inbound_transport_manager.transports,
            self.outbound_transport_manager.registered_transports,
        )

        # Debug settings
        test_seed = self.settings.get("debug.seed")
        if self.settings.get("debug.enabled"):
            if not test_seed:
                test_seed = "testseed000000000000000000000001"
        if test_seed:
            _did_info = await context.wallet.create_local_did(test_seed)

        # Auto-send an invitation to another agent
        send_invite_to = self.settings.get("debug.send_invitation_to")
        try:
            if send_invite_to:
                mgr = ConnectionManager(context)
                invitation = await mgr.create_invitation(context.default_label, context.default_endpoint)
                await mgr.store_invitation(invitation, False)
                await mgr.send_invitation(invitation, send_invite_to)
        except Exception:
            self.logger.exception("Error sending invitation")


    async def inbound_message_router(self, message_body: Union[str, bytes], transport_type: str, reply: Coroutine = None):
        context = await self.context.expand_message(message_body, transport_type)
        result = await self.dispatcher.dispatch(context, self.outbound_message_router, reply)
        # TODO: need to use callback instead?
        #       respond immediately after message parse in case of req-res transport?
        return result.serialize() if result else None

    async def outbound_message_router(self, message: AgentMessage, target: ConnectionTarget) -> None:
        payload = await self.context.compact_message(message, target)
        await self.outbound_transport_manager.send_message(payload, target.endpoint)
