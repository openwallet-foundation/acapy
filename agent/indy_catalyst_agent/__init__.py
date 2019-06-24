"""Entrypoint."""

import os

import argparse
import asyncio

from aiohttp import ClientSession

from .conductor import Conductor
from .defaults import default_protocol_registry
from .logging import LoggingConfigurator
from .postgres import load_postgres_plugin
from .transport.inbound.base import InboundTransportConfiguration

PARSER = argparse.ArgumentParser(description="Runs an Indy Agent.")


PARSER.add_argument(
    "-it",
    "--inbound-transport",
    dest="inbound_transports",
    type=str,
    action="append",
    nargs=3,
    required=True,
    metavar=("<module>", "<host>", "<port>"),
    help="Choose which interface(s) to listen on",
)

PARSER.add_argument(
    "-ot",
    "--outbound-transport",
    dest="outbound_transports",
    type=str,
    action="append",
    required=True,
    metavar="<module>",
    help="Choose which outbound transport handlers to register",
)

PARSER.add_argument(
    "--logging-config",
    dest="logging_config",
    type=str,
    metavar="<path-to-config>",
    default=None,
    help="Specifies a custom logging configuration file",
)

PARSER.add_argument(
    "--log-level",
    dest="log_level",
    type=str,
    metavar="<log-level>",
    default=None,
    help="Specifies a custom logging level "
    + "(debug, info, warning, error, critical)",
)

PARSER.add_argument(
    "-e",
    "--endpoint",
    type=str,
    metavar="<endpoint>",
    help="Specify the default endpoint to use when "
    + "creating connection invitations and requests",
)

PARSER.add_argument(
    "-l",
    "--label",
    type=str,
    metavar="<label>",
    help="Specify the default label to use when creating"
    + " connection invitations and requests",
)


PARSER.add_argument(
    "--seed",
    type=str,
    metavar="<wallet-seed>",
    help="Seed to use when creating the public DID",
)

PARSER.add_argument(
    "--storage-type",
    type=str,
    metavar="<storage-type>",
    help="Specify the storage implementation to use",
)

PARSER.add_argument(
    "--wallet-key",
    type=str,
    metavar="<wallet-key>",
    help="Specify the master key value to use when opening the wallet",
)

PARSER.add_argument(
    "--wallet-name", type=str, metavar="<wallet-name>", help="Specify the wallet name"
)

PARSER.add_argument(
    "--wallet-type",
    type=str,
    metavar="<wallet-type>",
    help="Specify the wallet implementation to use",
)

PARSER.add_argument(
    "--wallet-storage-type",
    type=str,
    metavar="<storage-type>",
    help="Specify the wallet storage implementation to use",
)

PARSER.add_argument(
    "--wallet-storage-config",
    type=str,
    metavar="<storage-config>",
    help="Specify the storage configuration to use (required for postgres) "
    + 'e.g., \'{"url":"localhost:5432"}\'',
)

PARSER.add_argument(
    "--wallet-storage-creds",
    type=str,
    metavar="<storage-creds>",
    help="Specify the storage credentials to use (required for postgres) "
    + 'e.g., \'{"account":"postgres","password":"mysecretpassword","admin_account":"postgres","admin_password":"mysecretpassword"}\'',
)

PARSER.add_argument(
    "--pool-name", type=str, metavar="<pool-name>", help="Specify the pool name"
)

PARSER.add_argument(
    "--genesis-transactions",
    type=str,
    dest="genesis_transactions",
    metavar="<genesis-transactions>",
    help="Specify the genesis transactions as a string",
)

PARSER.add_argument(
    "--genesis-url",
    type=str,
    dest="genesis_url",
    metavar="<genesis-url>",
    help="Specify a url from which to fetch the genesis transactions",
)

PARSER.add_argument(
    "--admin",
    type=str,
    nargs=2,
    metavar=("<host>", "<port>"),
    help="Enable the administration API on a given host and port",
)

PARSER.add_argument("--debug", action="store_true", help="Enable debugging features")

PARSER.add_argument(
    "--debug-seed",
    dest="debug_seed",
    type=str,
    metavar="<debug-did-seed>",
    help="Specify the debug seed to use",
)

PARSER.add_argument(
    "--debug-connections",
    action="store_true",
    help="Enable additional logging around connections",
)

PARSER.add_argument(
    "--accept-invites", action="store_true", help="Auto-accept connection invitations"
)

PARSER.add_argument(
    "--accept-requests", action="store_true", help="Auto-accept connection requests"
)

PARSER.add_argument(
    "--auto-ping-connection",
    action="store_true",
    help="Automatically send a trust ping when a connection response is accepted",
)

PARSER.add_argument(
    "--auto-respond-messages",
    action="store_true",
    help="Auto-respond to basic messages",
)

PARSER.add_argument(
    "--auto-respond-credential-offer",
    action="store_true",
    help="Auto-respond to credential offers with credential request",
)

PARSER.add_argument(
    "--auto-respond-presentation-request",
    action="store_true",
    help="Auto-respond to presentation requests with a presentation "
    + "if exactly one credential exists to satisfy the request",
)

PARSER.add_argument(
    "--auto-verify-presentation",
    action="store_true",
    help="Automatically verify a presentation when it is received",
)

PARSER.add_argument(
    "--no-receive-invites",
    action="store_true",
    help="Disable the receive invitations administration function",
)

PARSER.add_argument(
    "--help-link",
    type=str,
    metavar="<help-url>",
    help="Define the help URL for the administration interface",
)

PARSER.add_argument(
    "--invite",
    action="store_true",
    help="Generate and print a new connection invitation URL",
)

PARSER.add_argument(
    "--send-invite",
    type=str,
    metavar="<agent-endpoint>",
    help="Specify an endpoint to send an invitation to",
)

PARSER.add_argument(
    "--timing",
    action="store_true",
    help="Including timing information in response messages",
)

PARSER.add_argument(
    "--protocol",
    dest="external_protocols",
    type=str,
    action="append",
    required=False,
    metavar="<module>",
    help="Provide external protocol modules",
)


async def start(
    inbound_transport_configs: list, outbound_transports: list, settings: dict
):
    """Start."""
    registry = default_protocol_registry()
    conductor = Conductor(
        inbound_transport_configs, outbound_transports, registry, settings
    )
    await conductor.start()


async def get_genesis_transactions(
    genesis_url: str
):
    """Get genesis transactions."""
    headers = {}
    headers["Content-Type"] = "application/json"
    async with ClientSession() as client_session:
        response = await client_session.get(genesis_url, headers=headers)
        genesis_txns = await response.text()
        return genesis_txns


def main():
    """Entrypoint."""
    args = PARSER.parse_args()
    settings = {}

    inbound_transport_configs = []

    inbound_transports = args.inbound_transports
    for transport in inbound_transports:
        module = transport[0]
        host = transport[1]
        port = transport[2]
        inbound_transport_configs.append(
            InboundTransportConfiguration(module=module, host=host, port=port)
        )

    outbound_transports = args.outbound_transports

    logging_config = args.logging_config
    log_level = args.log_level or os.getenv("LOG_LEVEL")
    LoggingConfigurator.configure(logging_config, log_level)

    if args.endpoint:
        settings["default_endpoint"] = args.endpoint
    if args.label:
        settings["default_label"] = args.label

    if args.genesis_url:
        settings["ledger.genesis_url"] = args.genesis_url
        loop = asyncio.get_event_loop()
        settings["ledger.genesis_transactions"] = loop.run_until_complete(
            get_genesis_transactions(args.genesis_url)
        )
    elif args.genesis_transactions:
        settings["ledger.genesis_transactions"] = args.genesis_transactions

    if args.storage_type:
        settings["storage.type"] = args.storage_type

    if args.seed:
        settings["wallet.seed"] = args.seed
    if args.wallet_key:
        settings["wallet.key"] = args.wallet_key
    if args.wallet_name:
        settings["wallet.name"] = args.wallet_name
    if args.wallet_storage_type:
        settings["wallet.storage_type"] = args.wallet_storage_type
    if args.wallet_type:
        settings["wallet.type"] = args.wallet_type
        # load postgres plug-in here
        # TODO where should this live?
        if args.wallet_storage_type == "postgres_storage":
            load_postgres_plugin()
    if args.wallet_storage_config:
        settings["wallet.storage_config"] = args.wallet_storage_config
    if args.wallet_storage_creds:
        settings["wallet.storage_creds"] = args.wallet_storage_creds

    if args.admin:
        settings["admin.enabled"] = True
        settings["admin.host"] = args.admin[0]
        settings["admin.port"] = args.admin[1]
        if args.help_link:
            settings["admin.help_link"] = args.help_link
        if args.no_receive_invites:
            settings["admin.no_receive_invites"] = True

    if args.debug:
        settings["debug.enabled"] = True
    if args.debug_connections:
        settings["debug.connections"] = True
    if args.debug_seed:
        settings["debug.seed"] = args.debug_seed
    if args.invite:
        settings["debug.print_invitation"] = True
    if args.send_invite:
        settings["debug.send_invitation_to"] = args.send_invite

    if args.auto_respond_credential_offer:
        settings["auto_respond_credential_offer"] = True
    if args.auto_respond_presentation_request:
        settings["auto_respond_presentation_request"] = True
    if args.auto_verify_presentation:
        settings["auto_verify_presentation"] = True

    if args.accept_invites:
        settings["accept_invites"] = True
    if args.accept_requests:
        settings["accept_requests"] = True
    if args.auto_ping_connection:
        settings["auto_ping_connection"] = True
    if args.auto_respond_messages:
        settings["debug.auto_respond_messages"] = True

    if args.timing:
        settings["timing.enabled"] = True

    if args.external_protocols:
        settings["external_protocols"] = args.external_protocols

    loop = asyncio.get_event_loop()
    try:
        # asyncio.ensure_future(
        #     start(inbound_transport_configs, outbound_transports, settings), loop=loop
        # )
        loop.run_until_complete(
            start(inbound_transport_configs, outbound_transports, settings)
        )
        loop.run_forever()
    except KeyboardInterrupt:
        print("\nShutting down")


if __name__ == "__main__":
    main()  # pragma: no cover
