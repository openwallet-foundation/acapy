import argparse
import asyncio
import os
import signal

from .conductor import Conductor
from .defaults import default_message_factory
from .logging import LoggingConfigurator
from .transport.inbound import InboundTransportConfiguration

from .version import __version__


parser = argparse.ArgumentParser(description="Runs an Indy Agent.")

parser.add_argument(
    "--inbound-transport",
    dest="inbound_transports",
    type=str,
    action="append",
    nargs=3,
    required=True,
    metavar=("<module>", "<host>", "<port>"),
    help="Choose which interface(s) to listen on",
)

parser.add_argument(
    "--outbound-transport",
    dest="outbound_transports",
    type=str,
    action="append",
    required=True,
    metavar="<module>",
    help="Choose which outbound transport handlers to register",
)

parser.add_argument(
    "--logging-config",
    dest="logging_config",
    type=str,
    metavar="<path-to-config>",
    default=None,
    help="Specifies a custom logging configuration file",
)

parser.add_argument(
    "--log-level",
    dest="log_level",
    type=str,
    metavar="<log-level>",
    default=None,
    help="Specifies a custom logging level (debug, info, warning, error, critical)",
)


async def start(inbound_transport_configs, outbound_transports):
    factory = default_message_factory()
    conductor = Conductor(inbound_transport_configs, outbound_transports, factory)
    await conductor.start()


def main():
    args = parser.parse_args()

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

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(start(inbound_transport_configs, outbound_transports))
        loop.run_forever()
    except KeyboardInterrupt:
        print("\nShutting down")


if __name__ == "__main__":
    main()  # pragma: no cover
