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


def print_start_banner(host, port, proto):

    banner_length = 30

    banner_title_string = "Indy Catalyst Agent"
    banner_title_spacer = " " * (banner_length - len(banner_title_string))

    banner_border = ":" * (banner_length + 6)
    banner_spacer = "::" + " " * (banner_length + 2) + "::"

    host_port_string = f"{proto}: {host}:{port}"
    host_port_spacer = " " * (banner_length - len(host_port_string))

    version_string = f"ver: {__version__}"
    version_string_spacer = " " * (banner_length - len(version_string))

    print()
    print(f"{banner_border}")
    print(f":: {banner_title_string}{banner_title_spacer} ::")
    print(f"{banner_spacer}")
    print(f":: {host_port_string}{host_port_spacer} ::")
    print(f"{banner_spacer}")
    print(f":: {version_string_spacer}{version_string} ::")
    print(f"{banner_border}")
    print()

def main():
    args = PARSER.parse_args()

    # Obtain required args
    transport = args.transport
    host = args.host
    port = args.port

    logging_config = args.logging_config

    LoggingConfigurator.configure(logging_config)

    print_start_banner(host, port, 'http')

    conductor = Conductor(transport, host, port)
    conductor.start()


if __name__ == "__main__":
    main()  # pragma: no cover
