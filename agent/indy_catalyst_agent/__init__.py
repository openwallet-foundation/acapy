import argparse

from .conductor import Conductor
from .logging import LoggingConfigurator

from .version import __version__

PARSER = argparse.ArgumentParser(description="Runs an Indy Agent.")
PARSER.add_argument(
    "--transport",
    dest="transport",
    type=str,
    default="http",
    choices=["http"],
    help="Specifies the upstream transport type.",
)
PARSER.add_argument(
    "--host",
    dest="host",
    type=str,
    default="0.0.0.0",
    help="Specifies the upstream transport host.",
)
PARSER.add_argument(
    "--port",
    dest="port",
    type=int,
    default=80,
    help="Specifies the upstream transport port.",
)

PARSER.add_argument(
    "--logging-config",
    dest="logging_config",
    type=str,
    default=None,
    help="Specifies a custom logging configuration file.",
)


def main():
    args = PARSER.parse_args()

    # Obtain required args
    transport = args.transport
    host = args.host
    port = args.port

    logging_config = args.logging_config

    LoggingConfigurator.configure(logging_config)

    conductor = Conductor(transport, host, port)
    conductor.start()


if __name__ == "__main__":
    main()  # pragma: no cover
