"""Utilities related to logging."""

import logging
from io import TextIOWrapper
from logging.config import fileConfig
from typing import TextIO

import pkg_resources

from ..version import __version__


DEFAULT_LOGGING_CONFIG_PATH = "aries_cloudagent.config:default_logging_config.ini"


def load_resource(path: str, encoding: str = None) -> TextIO:
    """
    Open a resource file located in a python package or the local filesystem.

    Args:
        path: The resource path in the form of `dir/file` or `package:dir/file`
    Returns:
        A file-like object representing the resource
    """
    components = path.rsplit(":", 1)
    try:
        if len(components) == 1:
            return open(components[0], encoding=encoding)
        else:
            bstream = pkg_resources.resource_stream(components[0], components[1])
            if encoding:
                return TextIOWrapper(bstream, encoding=encoding)
            return bstream
    except IOError:
        pass


class LoggingConfigurator:
    """Utility class used to configure logging and print an informative start banner."""

    @classmethod
    def configure(
        cls,
        logging_config_path: str = None,
        log_level: str = None,
        log_file: str = None,
    ):
        """
        Configure logger.

        :param logging_config_path: str: (Default value = None) Optional path to
            custom logging config

        :param log_level: str: (Default value = None)
        """
        if logging_config_path is not None:
            config_path = logging_config_path
        else:
            config_path = DEFAULT_LOGGING_CONFIG_PATH

        log_config = load_resource(config_path, "utf-8")
        if log_config:
            with log_config:
                fileConfig(log_config, disable_existing_loggers=False)
        else:
            logging.basicConfig(level=logging.WARNING)
            logging.root.warning(f"Logging config file not found: {config_path}")

        if log_file:
            logging.root.handlers.clear()
            logging.root.handlers.append(
                logging.FileHandler(log_file, encoding="utf-8")
            )

        if log_level:
            log_level = log_level.upper()
            logging.root.setLevel(log_level)

    @classmethod
    def print_banner(
        cls,
        agent_label,
        inbound_transports,
        outbound_transports,
        public_did,
        admin_server=None,
        banner_length=40,
        border_character=":",
    ):
        """
        Print a startup banner describing the configuration.

        Args:
            agent_label: Agent Label
            inbound_transports: Configured inbound transports
            outbound_transports: Configured outbound transports
            admin_server: Admin server info
            public_did: Public DID
            banner_length: (Default value = 40) Length of the banner
            border_character: (Default value = ":") Character to use in banner
            border
        """

        def lr_pad(content: str):
            """
            Pad string content with defined border character.

            Args:
                content: String content to pad
            """
            return (
                f"{border_character}{border_character}"
                + f" {content} {border_character}{border_character}"
            )

        banner_title_string = agent_label or "ACA"
        banner_title_spacer = " " * (banner_length - len(banner_title_string))

        banner_border = border_character * (banner_length + 6)
        banner_spacer = (
            f"{border_character}{border_character}"
            + " " * (banner_length + 2)
            + f"{border_character}{border_character}"
        )

        inbound_transports_subtitle_string = "Inbound Transports:"
        inbound_transports_subtitle_spacer = " " * (
            banner_length - len(inbound_transports_subtitle_string)
        )

        inbound_transport_strings = []
        for transport in inbound_transports.values():
            host_port_string = (
                f"  - {transport.scheme}://{transport.host}:{transport.port}"
            )
            host_port_spacer = " " * (banner_length - len(host_port_string))
            inbound_transport_strings.append((host_port_string, host_port_spacer))

        outbound_transports_subtitle_string = "Outbound Transports:"
        outbound_transports_subtitle_spacer = " " * (
            banner_length - len(outbound_transports_subtitle_string)
        )

        outbound_transport_strings = []
        schemes = set().union(
            *(transport.schemes for transport in outbound_transports.values())
        )
        for scheme in sorted(schemes):
            schema_string = f"  - {scheme}"
            scheme_spacer = " " * (banner_length - len(schema_string))
            outbound_transport_strings.append((schema_string, scheme_spacer))

        version_string = f"ver: {__version__}"
        version_string_spacer = " " * (banner_length - len(version_string))

        public_did_subtitle_string = "Public DID Information:"
        public_did_subtitle_spacer = " " * (
            banner_length - len(public_did_subtitle_string)
        )

        public_did_strings = []
        did_string = f"  - DID: {public_did}"
        did_spacer = " " * (banner_length - len(did_string))
        public_did_strings.append((did_string, did_spacer))

        admin_subtitle_string = "Administration API:"
        admin_subtitle_spacer = " " * (banner_length - len(admin_subtitle_string))

        admin_strings = []
        if admin_server:
            host_port_string = f"  - http://{admin_server.host}:{admin_server.port}"
            host_port_spacer = " " * (banner_length - len(host_port_string))
            admin_strings.append((host_port_string, host_port_spacer))
        else:
            disabled_string = "  - not enabled"
            disabled_spacer = " " * (banner_length - len(disabled_string))
            admin_strings.append((disabled_string, disabled_spacer))

        # Title
        print()
        print(f"{banner_border}")
        print(lr_pad(f"{banner_title_string}{banner_title_spacer}"))
        print(f"{banner_spacer}")
        print(f"{banner_spacer}")

        # Inbound transports
        print(
            lr_pad(
                str(inbound_transports_subtitle_string)
                + str(inbound_transports_subtitle_spacer)
            )
        )
        print(f"{banner_spacer}")
        for transport_string in inbound_transport_strings:
            print(lr_pad(f"{transport_string[0]}{transport_string[1]}"))
        print(f"{banner_spacer}")

        # Outbound transports
        print(
            lr_pad(
                str(outbound_transports_subtitle_string)
                + str(outbound_transports_subtitle_spacer)
            )
        )
        print(f"{banner_spacer}")
        for transport_string in outbound_transport_strings:
            print(lr_pad(f"{transport_string[0]}{transport_string[1]}"))
        print(f"{banner_spacer}")

        # DID info
        if public_did:
            print(
                lr_pad(
                    str(public_did_subtitle_string) + str(public_did_subtitle_spacer)
                )
            )
            print(f"{banner_spacer}")
            for public_did_string in public_did_strings:
                print(lr_pad(f"{public_did_string[0]}{public_did_string[1]}"))
            print(f"{banner_spacer}")

        # Admin server info
        print(lr_pad(str(admin_subtitle_string) + str(admin_subtitle_spacer)))
        print(f"{banner_spacer}")
        for admin_string in admin_strings:
            print(lr_pad(f"{admin_string[0]}{admin_string[1]}"))
        print(f"{banner_spacer}")
        print(lr_pad(f"{version_string_spacer}{version_string}"))
        print(f"{banner_border}")
        print()
        print("Listening...")
        print()
