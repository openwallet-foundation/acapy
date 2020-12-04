"""Http Transport classes and functions."""

import logging

from aiohttp import web

from ...messaging.error import MessageParseError
from ..wire_format import BaseWireFormat

from .base import BaseInboundTransport, InboundTransportSetupError
from ...wallet.models.wallet_record import WalletRecord
from ...multitenant.manager import (
    MultitenantManager,
    MultitenantManagerError,
)

LOGGER = logging.getLogger(__name__)


class HttpTransport(BaseInboundTransport):
    """Http Transport class."""

    def __init__(self, host: str, port: int, create_session, **kwargs) -> None:
        """
        Initialize an inbound HTTP transport instance.

        Args:
            host: Host to listen on
            port: Port to listen on
            create_session: Method to create a new inbound session

        """
        super().__init__("http", create_session, **kwargs)
        self.host = host
        self.port = port
        self.site: web.BaseSite = None

    async def make_application(self) -> web.Application:
        """Construct the aiohttp application."""
        app_args = {}
        if self.max_message_size:
            app_args["client_max_size"] = self.max_message_size
        app = web.Application(**app_args)
        app.add_routes([web.get("/", self.invite_message_handler)])
        app.add_routes([web.post("/", self.inbound_message_handler)])
        return app

    async def start(self) -> None:
        """
        Start this transport.

        Raises:
            InboundTransportSetupError: If there was an error starting the webserver

        """
        app = await self.make_application()
        runner = web.AppRunner(app)
        await runner.setup()
        self.site = web.TCPSite(runner, host=self.host, port=self.port)
        try:
            await self.site.start()
        except OSError:
            raise InboundTransportSetupError(
                "Unable to start webserver with host "
                + f"'{self.host}' and port '{self.port}'\n"
            )

    async def stop(self) -> None:
        """Stop this transport."""
        if self.site:
            await self.site.stop()
            self.site = None

    async def inbound_message_handler(self, request: web.BaseRequest):
        """
        Message handler for inbound messages.

        Args:
            request: aiohttp request object

        Returns:
            The web response

        """
        ctype = request.headers.get("content-type", "")
        if ctype.split(";", 1)[0].lower() == "application/json":
            body = await request.text()
        else:
            body = await request.read()

        client_info = {"host": request.host, "remote": request.remote}

        session = await self.create_session(
            accept_undelivered=True, can_respond=True, client_info=client_info
        )

        # MTODO: move to better place (relay class or something)
        # Simple relay functionality
        wire_format = self.wire_format or await session.context.inject(BaseWireFormat)
        recipient_keys = wire_format.get_recipient_keys(body) if wire_format else []
        if len(recipient_keys) > 0 and session.context.settings.get(
            "multitenant.enabled"
        ):
            LOGGER.info("searching for wallet associated with incoming message")
            try:
                # try to find subwallet
                multitenant_mgr = MultitenantManager(session.context)
                wallet_records = await multitenant_mgr.get_wallets_by_recipient_keys(
                    recipient_keys
                )

                # MTODO: what to do with multiple recipients?
                wallet_record = wallet_records[0]

                # MTODO: unamanged mode
                if wallet_record.key_management_mode == WalletRecord.MODE_MANAGED:
                    LOGGER.info(
                        "routing record found for subwallet %s, switching context",
                        wallet_record.wallet_record_id,
                    )
                    session.context = session.context.copy()
                    session.context.settings = session.context.settings.extend(
                        wallet_record.get_config_as_settings()
                    )
            except IndexError:
                # No wallet found. We'll use the normal session context
                pass
            except MultitenantManagerError:
                # MTODO: What does this mean?
                raise web.HTTPBadRequest()

        async with session:
            try:
                inbound = await session.receive(body)
            except MessageParseError:
                raise web.HTTPBadRequest()

            if inbound.receipt.direct_response_requested:
                response = await session.wait_response()

                # no more responses
                session.can_respond = False
                session.clear_response()

                if response:
                    if isinstance(response, bytes):
                        return web.Response(
                            body=response,
                            status=200,
                            headers={"Content-Type": "application/ssi-agent-wire"},
                        )
                    else:
                        return web.Response(
                            text=response,
                            status=200,
                            headers={"Content-Type": "application/json"},
                        )
        return web.Response(status=200)

    async def invite_message_handler(self, request: web.BaseRequest):
        """
        Message handler for invites.

        Args:
            request: aiohttp request object

        Returns:
            The web response

        """
        if request.query.get("c_i"):
            return web.Response(
                text="You have received a connection invitation. To accept the "
                "invitation, paste it into your agent application."
            )
        else:
            return web.Response(status=200)
