"""Command line option parsing."""

import abc
import os

from argparse import ArgumentParser, Namespace
from typing import Type

from .error import ArgsParseError

CAT_PROVISION = "general"
CAT_START = "start"


class ArgumentGroup(abc.ABC):
    """A class representing a group of related command line arguments."""

    GROUP_NAME = None

    @abc.abstractmethod
    def add_arguments(parser: ArgumentParser):
        """Add arguments to the provided argument parser."""

    @abc.abstractmethod
    def get_settings(args: Namespace) -> dict:
        """Extract settings from the parsed arguments."""


class group:
    """Decorator for registering argument groups."""

    _registered = []

    def __init__(self, *categories):
        """Initialize the decorator."""
        self.categories = tuple(categories)

    def __call__(self, group_cls: ArgumentGroup):
        """Register a class in the given categories."""
        setattr(group_cls, "CATEGORIES", self.categories)
        self._registered.append((self.categories, group_cls))
        return group_cls

    @classmethod
    def get_registered(cls, category: str = None):
        """Fetch the set of registered classes in a category."""
        return (
            grp
            for (cats, grp) in cls._registered
            if category is None or category in cats
        )


def load_argument_groups(parser: ArgumentParser, *groups: Type[ArgumentGroup]):
    """Log a set of argument groups into a parser.

    Returns:
        A callable to convert loaded arguments into a settings dictionary

    """
    group_inst = []
    for group in groups:
        g_parser = parser.add_argument_group(group.GROUP_NAME)
        inst = group()
        inst.add_arguments(g_parser)
        group_inst.append(inst)

    def get_settings(args: Namespace):
        settings = {}
        for group in group_inst:
            settings.update(group.get_settings(args))
        return settings

    return get_settings


@group(CAT_START)
class AdminGroup(ArgumentGroup):
    """Admin server settings."""

    GROUP_NAME = "Admin"

    def add_arguments(self, parser: ArgumentParser):
        """Add admin-specific command line arguments to the parser."""
        parser.add_argument(
            "--admin",
            type=str,
            nargs=2,
            metavar=("<host>", "<port>"),
            help="Enable the administration API on a given host and port",
        )
        parser.add_argument(
            "--admin-api-key",
            type=str,
            metavar="<api-key>",
            help="Set the api key for the admin API.",
        )
        parser.add_argument(
            "--admin-insecure-mode",
            action="store_true",
            help="Do not protect the admin API with token authentication.z",
        )
        parser.add_argument(
            "--no-receive-invites",
            action="store_true",
            help="Disable the receive invitations administration function",
        )
        parser.add_argument(
            "--help-link",
            type=str,
            metavar="<help-url>",
            help="Define the help URL for the administration interface",
        )
        parser.add_argument(
            "--webhook-url",
            action="append",
            metavar="<url>",
            help="Send webhooks to a given URL",
        )

    def get_settings(self, args: Namespace):
        """Extract admin settings."""
        settings = {}
        if args.admin:
            admin_api_key = args.admin_api_key
            admin_insecure_mode = args.admin_insecure_mode

            if (admin_api_key and admin_insecure_mode) or not (
                admin_api_key or admin_insecure_mode
            ):
                raise ArgsParseError(
                    "Either --admin-api-key or --admin-insecure-mode "
                    + "must be set but not both."
                )

            settings["admin.admin_api_key"] = admin_api_key
            settings["admin.admin_insecure_mode"] = admin_insecure_mode

            settings["admin.enabled"] = True
            settings["admin.host"] = args.admin[0]
            settings["admin.port"] = args.admin[1]
            if args.help_link:
                settings["admin.help_link"] = args.help_link
            if args.no_receive_invites:
                settings["admin.no_receive_invites"] = True
            hook_urls = list(args.webhook_url) if args.webhook_url else []
            hook_url = os.environ.get("WEBHOOK_URL")
            if hook_url:
                hook_urls.append(hook_url)
            settings["admin.webhook_urls"] = hook_urls
        return settings


@group(CAT_START)
class DebugGroup(ArgumentGroup):
    """Debug settings."""

    GROUP_NAME = "Debug"

    def add_arguments(self, parser: ArgumentParser):
        """Add debug command line arguments to the parser."""
        parser.add_argument(
            "--debug", action="store_true", help="Enable debugging features"
        )
        parser.add_argument(
            "--debug-seed",
            dest="debug_seed",
            type=str,
            metavar="<debug-did-seed>",
            help="Specify the debug seed to use",
        )
        parser.add_argument(
            "--debug-connections",
            action="store_true",
            help="Enable additional logging around connections",
        )
        parser.add_argument(
            "--debug-credentials",
            action="store_true",
            help="Enable additional logging around credential exchanges",
        )
        parser.add_argument(
            "--debug-presentations",
            action="store_true",
            help="Enable additional logging around presentation exchanges",
        )
        parser.add_argument(
            "--invite",
            action="store_true",
            help="Generate and print a new connection invitation URL",
        )

        parser.add_argument(
            "--auto-accept-invites",
            action="store_true",
            help="Auto-accept connection invitations",
        )
        parser.add_argument(
            "--auto-accept-requests",
            action="store_true",
            help="Auto-accept connection requests",
        )
        parser.add_argument(
            "--auto-respond-messages",
            action="store_true",
            help="Auto-respond to basic messages",
        )
        parser.add_argument(
            "--auto-respond-credential-offer",
            action="store_true",
            help="Auto-respond to credential offers with credential request",
        )
        parser.add_argument(
            "--auto-respond-presentation-request",
            action="store_true",
            help="Auto-respond to presentation requests with a presentation "
            + "if exactly one credential exists to satisfy the request",
        )
        parser.add_argument(
            "--auto-store-credential",
            action="store_true",
            help="Automatically store a credential upon receipt.",
        )
        parser.add_argument(
            "--auto-verify-presentation",
            action="store_true",
            help="Automatically verify a presentation when it is received",
        )

    def get_settings(self, args: Namespace) -> dict:
        """Extract debug settings."""
        settings = {}
        if args.debug:
            settings["debug.enabled"] = True
        if args.debug_connections:
            settings["debug.connections"] = True
        if args.debug_credentials:
            settings["debug.credentials"] = True
        if args.debug_presentations:
            settings["debug.presentations"] = True
        if args.debug_seed:
            settings["debug.seed"] = args.debug_seed
        if args.invite:
            settings["debug.print_invitation"] = True

        if args.auto_respond_credential_offer:
            settings["debug.auto_respond_credential_offer"] = True
        if args.auto_respond_presentation_request:
            settings["debug.auto_respond_presentation_request"] = True
        if args.auto_store_credential:
            settings["debug.auto_store_credential"] = True
        if args.auto_verify_presentation:
            settings["debug.auto_verify_presentation"] = True
        if args.auto_accept_invites:
            settings["debug.auto_accept_invites"] = True
        if args.auto_accept_requests:
            settings["debug.auto_accept_requests"] = True
        if args.auto_respond_messages:
            settings["debug.auto_respond_messages"] = True
        return settings


@group(CAT_PROVISION, CAT_START)
class GeneralGroup(ArgumentGroup):
    """General settings."""

    GROUP_NAME = "General"

    def add_arguments(self, parser: ArgumentParser):
        """Add general command line arguments to the parser."""
        parser.add_argument(
            "--storage-type",
            type=str,
            metavar="<storage-type>",
            help="Specify the storage implementation to use",
        )

    def get_settings(self, args: Namespace) -> dict:
        """Extract general settings."""
        settings = {}
        if args.storage_type:
            settings["storage.type"] = args.storage_type
        return settings


@group(CAT_START)
class LedgerGroup(ArgumentGroup):
    """Ledger settings."""

    GROUP_NAME = "Ledger"

    def add_arguments(self, parser: ArgumentParser):
        """Add ledger-specific command line arguments to the parser."""
        parser.add_argument(
            "--ledger-pool-name", type=str, metavar="<ledger-pool-name>", help="Specify the pool name"
        )
        parser.add_argument(
            "--genesis-transactions",
            type=str,
            dest="genesis_transactions",
            metavar="<genesis-transactions>",
            help="Specify the genesis transactions as a string",
        )
        parser.add_argument(
            "--genesis-url",
            type=str,
            dest="genesis_url",
            metavar="<genesis-url>",
            help="Specify a url from which to fetch the genesis transactions",
        )

    def get_settings(self, args: Namespace) -> dict:
        """Extract ledger settings."""
        settings = {}
        if args.genesis_url:
            settings["ledger.genesis_url"] = args.genesis_url
        elif args.genesis_transactions:
            settings["ledger.genesis_transactions"] = args.genesis_transactions
        if args.ledger_pool_name:
            settings["ledger.pool_name"] = args.ledger_pool_name
        return settings


@group(CAT_PROVISION, CAT_START)
class LoggingGroup(ArgumentGroup):
    """Logging settings."""

    GROUP_NAME = "Logging"

    def add_arguments(self, parser: ArgumentParser):
        """Add logging-specific command line arguments to the parser."""
        parser.add_argument(
            "--log-config",
            dest="log_config",
            type=str,
            metavar="<path-to-config>",
            default=None,
            help="Specifies a custom logging configuration file",
        )
        parser.add_argument(
            "--log-file",
            dest="log_file",
            type=str,
            metavar="<log-file>",
            default=None,
            help="Redirect log output to a named file",
        )
        parser.add_argument(
            "--log-level",
            dest="log_level",
            type=str,
            metavar="<log-level>",
            default=None,
            help="Specifies a custom logging level "
            + "(debug, info, warning, error, critical)",
        )

    def get_settings(self, args: Namespace) -> dict:
        """Extract logging settings."""
        settings = {}
        if args.log_config:
            settings["log.config"] = args.log_config
        if args.log_file:
            settings["log.file"] = args.log_file
        if args.log_level:
            settings["log.level"] = args.log_level
        return settings


@group(CAT_START)
class ProtocolGroup(ArgumentGroup):
    """Protocol settings."""

    def add_arguments(self, parser: ArgumentParser):
        """Add protocol-specific command line arguments to the parser."""
        parser.add_argument(
            "--protocol",
            dest="external_protocols",
            type=str,
            action="append",
            required=False,
            metavar="<module>",
            help="Provide external protocol modules",
        )
        parser.add_argument(
            "--auto-ping-connection",
            action="store_true",
            help="Automatically send a trust ping when a "
            + "connection response is accepted",
        )
        parser.add_argument(
            "--public-invites",
            action="store_true",
            help="Send invitations and receive requests via the public DID",
        )
        parser.add_argument(
            "--timing",
            action="store_true",
            help="Including timing information in response messages",
        )

    def get_settings(self, args: Namespace) -> dict:
        """Get protocol settings."""
        settings = {}
        if args.external_protocols:
            settings["external_protocols"] = args.external_protocols
        if args.auto_ping_connection:
            settings["auto_ping_connection"] = True
        if args.public_invites:
            settings["public_invites"] = True
        if args.timing:
            settings["timing.enabled"] = True
        return settings


@group(CAT_START)
class TransportGroup(ArgumentGroup):
    """Transport settings."""

    GROUP_NAME = "Transport"

    def add_arguments(self, parser: ArgumentParser):
        """Add transport-specific command line arguments to the parser."""
        parser.add_argument(
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

        parser.add_argument(
            "-ot",
            "--outbound-transport",
            dest="outbound_transports",
            type=str,
            action="append",
            required=True,
            metavar="<module>",
            help="Choose which outbound transport handlers to register",
        )

        parser.add_argument(
            "-e",
            "--endpoint",
            type=str,
            metavar="<endpoint>",
            help="Specify the default endpoint to use when "
            + "creating connection invitations and requests",
        )

        parser.add_argument(
            "-l",
            "--label",
            type=str,
            metavar="<label>",
            help="Specify the default label to use when creating"
            + " connection invitations and requests",
        )

    def get_settings(self, args: Namespace):
        """Extract transport settings."""
        settings = {}
        settings["transport.inbound_configs"] = args.inbound_transports
        settings["transport.outbound_configs"] = args.outbound_transports

        if args.endpoint:
            settings["default_endpoint"] = args.endpoint
        if args.label:
            settings["default_label"] = args.label
        return settings


@group(CAT_PROVISION, CAT_START)
class WalletGroup(ArgumentGroup):
    """Wallet settings."""

    GROUP_NAME = "Wallet"

    def add_arguments(self, parser: ArgumentParser):
        """Add wallet-specific command line arguments to the parser."""
        parser.add_argument(
            "--seed",
            type=str,
            metavar="<wallet-seed>",
            help="Seed to use when creating the public DID",
        )
        parser.add_argument(
            "--wallet-key",
            type=str,
            metavar="<wallet-key>",
            help="Specify the master key value to use when opening the wallet",
        )
        parser.add_argument(
            "--wallet-name",
            type=str,
            metavar="<wallet-name>",
            help="Specify the wallet name",
        )
        parser.add_argument(
            "--wallet-type",
            type=str,
            metavar="<wallet-type>",
            help="Specify the wallet implementation to use",
        )
        parser.add_argument(
            "--wallet-storage-type",
            type=str,
            metavar="<storage-type>",
            help="Specify the wallet storage implementation to use",
        )
        parser.add_argument(
            "--wallet-storage-config",
            type=str,
            metavar="<storage-config>",
            help="Specify the storage configuration to use (required for postgres) "
            + 'e.g., \'{"url":"localhost:5432"}\'',
        )
        parser.add_argument(
            "--wallet-storage-creds",
            type=str,
            metavar="<storage-creds>",
            help="Specify the storage credentials to use (required for postgres) "
            + 'e.g., \'{"account":"postgres","password":"mysecretpassword",'
            + '"admin_account":"postgres","admin_password":"mysecretpassword"}\'',
        )

    def get_settings(self, args: Namespace) -> dict:
        """Extract wallet settings."""
        settings = {}
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
        if args.wallet_storage_config:
            settings["wallet.storage_config"] = args.wallet_storage_config
        if args.wallet_storage_creds:
            settings["wallet.storage_creds"] = args.wallet_storage_creds
        return settings
