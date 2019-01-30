from os import path

from logging.config import fileConfig
from ..version import __version__
from logging import getLogger
from logging.config import fileConfig
from os import path


class LoggingConfigurator:
    @classmethod
    def configure(cls, logging_config_path: str = None, log_level: str = None):
        if logging_config_path is not None:
            config_path = logging_config_path
        else:
            config_path = path.join(
                path.dirname(path.abspath(__file__)), "default_logging_config.ini"
            )

        fileConfig(config_path, disable_existing_loggers=True)

        if log_level:
            log_level = log_level.upper()
            getLogger().setLevel(log_level)

    @classmethod
    def print_banner(
        cls,
        inbound_transports,
        outbound_transports,
        banner_length=40,
        border_character=":",
    ):
        def lr_pad(content):
            return f"{border_character}{border_character} {content} {border_character}{border_character}"

        banner_title_string = "Indy Catalyst Agent"
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
        for transport in inbound_transports:
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
        for schemes in outbound_transports:
            for scheme in schemes:
                schema_string = f"  - {scheme}"
                scheme_spacer = " " * (banner_length - len(schema_string))
                outbound_transport_strings.append((schema_string, scheme_spacer))

        version_string = f"ver: {__version__}"
        version_string_spacer = " " * (banner_length - len(version_string))

        print()
        print(f"{banner_border}")
        print(lr_pad(f"{banner_title_string}{banner_title_spacer}"))
        print(f"{banner_spacer}")
        print(f"{banner_spacer}")
        print(
            lr_pad(
                f"{inbound_transports_subtitle_string}{inbound_transports_subtitle_spacer}"
            )
        )
        print(f"{banner_spacer}")
        for transport_string in inbound_transport_strings:
            print(lr_pad(f"{transport_string[0]}{transport_string[1]}"))
        print(f"{banner_spacer}")
        print(f"{banner_spacer}")
        print(
            lr_pad(
                f"{outbound_transports_subtitle_string}{outbound_transports_subtitle_spacer}"
            )
        )
        print(f"{banner_spacer}")
        for transport_string in outbound_transport_strings:
            print(lr_pad(f"{transport_string[0]}{transport_string[1]}"))
        print(f"{banner_spacer}")
        print(lr_pad(f"{version_string_spacer}{version_string}"))
        print(f"{banner_border}")
        print()
        print("Listening...")
        print()
