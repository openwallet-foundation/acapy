"""Entrypoint."""

import argparse
import asyncio
import os

from .conductor import Conductor
from .defaults import default_message_factory
from .logging import LoggingConfigurator
from .transport.inbound import InboundTransportConfiguration

# from .version import __version__


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

PARSER.add_argument("--debug", action="store_true", help="Enable debugging features")

PARSER.add_argument(
    "--seed", type=str, metavar="<did-seed>", help="Specify the default seed to use"
)

PARSER.add_argument(
    "--invite",
    type=str,
    metavar="<agent-endpoint>",
    help="Specify an endpoint to send an invitation to",
)


async def start(inbound_transport_configs, outbound_transports, settings: dict):
    """
    Start.

    Args:
        inbound_transport_configs
    """
    factory = default_message_factory()
    conductor = Conductor(
        inbound_transport_configs, outbound_transports, factory, settings
    )
    await conductor.start()


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

    if args.wallet_key:
        settings["wallet.key"] = args.wallet_key
    if args.wallet_name:
        settings["wallet.name"] = args.wallet_name
    if args.wallet_type:
        settings["wallet.type"] = args.wallet_type

    if args.debug:
        settings["debug.enabled"] = True
    if args.seed:
        settings["debug.seed"] = args.seed
    if args.invite:
        settings["debug.send_invitation_to"] = args.invite

    loop = asyncio.get_event_loop()
    try:
        asyncio.ensure_future(
            start(inbound_transport_configs, outbound_transports, settings), loop=loop
        )
        loop.run_forever()
    except KeyboardInterrupt:
        print("\nShutting down")


if __name__ == "__main__":
    main()  # pragma: no cover
