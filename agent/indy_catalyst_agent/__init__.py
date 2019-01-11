import argparse

from .conductor import Conductor

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


def main():
    args = PARSER.parse_args()

    # Obtain required args
    transport = args.transport
    host = args.host
    port = args.port

    conductor = Conductor(transport, host, port)
    conductor.start()


if __name__ == "__main__":
    main() # pragma: no cover
