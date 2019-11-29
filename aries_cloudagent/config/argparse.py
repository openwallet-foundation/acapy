"""Command line option parsing."""

import abc
import os

from argparse import ArgumentParser, Namespace
from typing import Type

from .error import ArgsParseError
from .util import ByteSize

CAT_PROVISION = "general"
CAT_START = "start"


class ArgumentGroup(abc.ABC):
    """A class representing a group of related command line arguments."""

    GROUP_NAME = None

    @abc.abstractmethod
    def add_arguments(self, parser: ArgumentParser):
        """Add arguments to the provided argument parser."""

    @abc.abstractmethod
    def get_settings(self, args: Namespace) -> dict:
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
            help="Specify the host and port on which to run the administrative server.\
            If not provided, no admin server is made available.",
        )
        parser.add_argument(
            "--admin-api-key",
            type=str,
            metavar="<api-key>",
            help="Protect all admin endpoints with the provided API key.\
            API clients (e.g. the controller) must pass the key in the HTTP\
            header using 'X-API-Key: <api key>'. Either this parameter or the\
            '--admin-insecure-mode' parameter MUST be specified.",
        )
        parser.add_argument(
            "--admin-insecure-mode",
            action="store_true",
            help="Run the admin web server in insecure mode. DO NOT USE FOR\
            PRODUCTION DEPLOYMENTS. The admin server will be publicly available\
            to anyone who has access to the interface. Either this parameter or\
            the '--api-key' parameter MUST be specified.",
        )
        parser.add_argument(
            "--no-receive-invites",
            action="store_true",
            help="Prevents an agent from receiving invites by removing the\
            '/connections/receive-invite' route from the administrative\
            interface. Default: false.",
        )
        parser.add_argument(
            "--help-link",
            type=str,
            metavar="<help-url>",
            help="A URL to an administrative interface help web page that a controller\
            user interface can get from the agent and provide as a link to users.",
        )
        parser.add_argument(
            "--webhook-url",
            action="append",
            metavar="<url>",
            help="Send webhooks containing internal state changes to the specified\
            URL. This is useful for a controller to monitor agent events and respond\
            to those events using the admin API. If not specified, webhooks are not\
            published by the agent.",
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
            "--debug",
            action="store_true",
            help="Enables a remote debugging service that can be accessed\
            using ptvsd for Visual Studio Code. The framework will wait\
            for the debugger to connect at start-up. Default: false."
        )
        parser.add_argument(
            "--debug-seed",
            dest="debug_seed",
            type=str,
            metavar="<debug-did-seed>",
            help="Specify the debug seed to use.",
        )
        parser.add_argument(
            "--debug-connections",
            action="store_true",
            help="Enable additional logging around connections. Default: false.",
        )
        parser.add_argument(
            "--debug-credentials",
            action="store_true",
            help="Enable additional logging around credential exchanges.\
            Default: false.",
        )
        parser.add_argument(
            "--debug-presentations",
            action="store_true",
            help="Enable additional logging around presentation exchanges.\
            Default: false.",
        )
        parser.add_argument(
            "--invite",
            action="store_true",
            help="After startup, generate and print a new connection invitation\
            URL. Default: false.",
        )
        parser.add_argument(
            "--invite-role",
            dest="invite_role",
            type=str,
            metavar="<role>",
            help="Specify the role of the generated invitation."
        )
        parser.add_argument(
            "--invite-label",
            dest="invite_label",
            type=str,
            metavar="<label>",
            help="Specify the label of the generated invitation."
        )
        parser.add_argument(
            "--invite-multi-use",
            action="store_true",
            help="Flag specifying the generated invite should be multi-use."
        )
        parser.add_argument(
            "--invite-public",
            action="store_true",
            help="Flag specifying the generated invite should be public."
        )
        parser.add_argument(
            "--test-suite-endpoint",
            type=str,
            metavar="<endpoint>",
            help="URL endpoint for sending messages to the test suite agent."
        )

        parser.add_argument(
            "--auto-accept-invites",
            action="store_true",
            help="Automatically accept invites without firing a webhook event or\
            waiting for an admin request. Default: false.",
        )
        parser.add_argument(
            "--auto-accept-requests",
            action="store_true",
            help="Automatically connection requests without firing a webhook event\
            or waiting for an admin request. Default: false.",
        )
        parser.add_argument(
            "--auto-respond-messages",
            action="store_true",
            help="Automatically respond to basic messages indicating the message was\
            received. Default: false.",
        )
        parser.add_argument(
            "--auto-respond-credential-proposal",
            action="store_true",
            help="Auto-respond to credential proposals with corresponding "
            + "credential offers",
        )
        parser.add_argument(
            "--auto-respond-credential-offer",
            action="store_true",
            help="Automatically respond to Indy credential offers with a credential\
            request. Default: false",
        )
        parser.add_argument(
            "--auto-respond-credential-request",
            action="store_true",
            help="Auto-respond to credential requests with corresponding credentials",
        )
        parser.add_argument(
            "--auto-respond-presentation-proposal",
            action="store_true",
            help="Auto-respond to presentation proposals with corresponding "
            + "presentation requests",
        )
        parser.add_argument(
            "--auto-respond-presentation-request",
            action="store_true",
            help="Automatically respond to Indy presentation requests with a\
            constructed presentation if exactly one credential can be retrieved\
            for every referent in the presentation request. Default: false.",
        )
        parser.add_argument(
            "--auto-store-credential",
            action="store_true",
            help="Automatically store an issued credential upon receipt.\
            Default: false.",
        )
        parser.add_argument(
            "--auto-verify-presentation",
            action="store_true",
            help="Automatically verify a presentation when it is received.\
            Default: false.",
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
        if args.invite_role:
            settings["debug.invite_role"] = args.invite_role
        if args.invite_label:
            settings["debug.invite_label"] = args.invite_label
        if args.invite_multi_use:
            settings["debug.invite_multi_use"] = True
        if args.invite_public:
            settings["debug.invite_public"] = True
        if args.test_suite_endpoint:
            settings["debug.test_suite_endpoint"] = args.test_suite_endpoint

        if args.auto_respond_credential_proposal:
            settings["debug.auto_respond_credential_proposal"] = True
        if args.auto_respond_credential_offer:
            settings["debug.auto_respond_credential_offer"] = True
        if args.auto_respond_credential_request:
            settings["debug.auto_respond_credential_request"] = True
        if args.auto_respond_presentation_proposal:
            settings["debug.auto_respond_presentation_proposal"] = True
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
            "--plugin",
            dest="external_plugins",
            type=str,
            action="append",
            required=False,
            metavar="<module>",
            help="Load <module> as external plugin module. Multiple\
            instances of this parameter can be specified.",
        )
        parser.add_argument(
            "--storage-type",
            type=str,
            metavar="<storage-type>",
            help="Specifies the type of storage provider to use for the internal\
            storage engine. This storage interface is used to store internal state.\
            Supported internal storage types are 'basic' (memory) and 'indy'.",
        )

    def get_settings(self, args: Namespace) -> dict:
        """Extract general settings."""
        settings = {}
        if args.external_plugins:
            settings["external_plugins"] = args.external_plugins
        if args.storage_type:
            settings["storage.type"] = args.storage_type
        return settings


@group(CAT_START, CAT_PROVISION)
class LedgerGroup(ArgumentGroup):
    """Ledger settings."""

    GROUP_NAME = "Ledger"

    def add_arguments(self, parser: ArgumentParser):
        """Add ledger-specific command line arguments to the parser."""
        parser.add_argument(
            "--ledger-pool-name",
            type=str,
            metavar="<ledger-pool-name>",
            help="Specifies the name of the indy pool to be opened.\
            This is useful if you have multiple pool configurations.",
        )
        parser.add_argument(
            "--genesis-transactions",
            type=str,
            dest="genesis_transactions",
            metavar="<genesis-transactions>",
            help="Specifies the genesis transactions to use to connect to\
            an Hyperledger Indy ledger. The transactions are provided as string\
            of JSON e.g. '{\"reqSignature\":{},\"txn\":{\"data\":{\"d... <snip>'",
        )
        parser.add_argument(
            "--genesis-file",
            type=str,
            dest="genesis_file",
            metavar="<genesis-file>",
            help="Specifies a local file from which to read the genesis transactions.",
        )
        parser.add_argument(
            "--genesis-url",
            type=str,
            dest="genesis_url",
            metavar="<genesis-url>",
            help="Specifies the url from which to download the genesis\
            transactions. For example, if you are using 'von-network',\
            the URL might be 'http://localhost:9000/genesis'.\
            Genesis transactions URLs are available for the Sovrin test/main networks.",
        )

    def get_settings(self, args: Namespace) -> dict:
        """Extract ledger settings."""
        settings = {}
        if args.genesis_url:
            settings["ledger.genesis_url"] = args.genesis_url
        elif args.genesis_file:
            settings["ledger.genesis_file"] = args.genesis_file
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
            help="Overrides the output destination for the root logger (as defined\
            by the log config file) to the named <log-file>.",
        )
        parser.add_argument(
            "--log-level",
            dest="log_level",
            type=str,
            metavar="<log-level>",
            default=None,
            help="Specifies a custom logging level as one of:\
            ('debug', 'info', 'warning', 'error', 'critical')",
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

    GROUP_NAME = "Protocol"

    def add_arguments(self, parser: ArgumentParser):
        """Add protocol-specific command line arguments to the parser."""
        parser.add_argument(
            "--auto-ping-connection",
            action="store_true",
            help="Automatically send a trust ping immediately after a\
            connection response is accepted. Some agents require this before\
            marking a connection as 'active'. Default: false.",
        )
        parser.add_argument(
            "--invite-base-url",
            type=str,
            metavar="<base-url>",
            help="Base URL to use when formatting connection invitations in URL format."
        )
        parser.add_argument(
            "--monitor-ping",
            action="store_true",
            help="Send a webhook when a ping is sent or received.",
        )
        parser.add_argument(
            "--public-invites",
            action="store_true",
            help="Send invitations out, and receive connection requests,\
            using the public DID for the agent. Default: false.",
        )
        parser.add_argument(
            "--timing",
            action="store_true",
            help="Include timing information in response messages.",
        )
        parser.add_argument(
            "--timing-log",
            type=str,
            metavar="<log-path>",
            help="Write timing information to a given log file.",
        )

    def get_settings(self, args: Namespace) -> dict:
        """Get protocol settings."""
        settings = {}
        if args.auto_ping_connection:
            settings["auto_ping_connection"] = True
        if args.invite_base_url:
            settings["invite_base_url"] = args.invite_base_url
        if args.monitor_ping:
            settings["debug.monitor_ping"] = args.monitor_ping
        if args.public_invites:
            settings["public_invites"] = True
        if args.timing:
            settings["timing.enabled"] = True
        if args.timing_log:
            settings["timing.log_file"] = args.timing_log
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
            help="REQUIRED. Defines the inbound transport(s) on which the agent\
            listens for receiving messages from other agents. This parameter can\
            be specified multiple times to create multiple interfaces.\
            Supported inbound transport types are 'http' and 'ws'.",
        )
        parser.add_argument(
            "-ot",
            "--outbound-transport",
            dest="outbound_transports",
            type=str,
            action="append",
            required=True,
            metavar="<module>",
            help="REQUIRED. Defines the outbound transport(s) on which the agent\
            will send outgoing messages to other agents. This parameter can be passed\
            multiple times to supoort multiple transport types. Supported outbound\
            transport types are 'http' and 'ws'.",
        )
        parser.add_argument(
            "-e",
            "--endpoint",
            type=str,
            nargs="+",
            metavar="<endpoint>",
            help="Specifies the endpoints to put into DIDDocs\
            to inform other agents of where they should send messages destined\
            for this agent. Each endpoint could be one of the specified inbound\
            transports for this agent, or the endpoint could be that of\
            another agent (e.g. 'https://example.com/agent-endpoint') if the\
            routing of messages to this agent by a mediator is configured.\
            The first endpoint specified will be used in invitations.\
            The endpoints are used in the formation of a connection \
            with another agent.",
        )
        parser.add_argument(
            "-l",
            "--label",
            type=str,
            metavar="<label>",
            help="Specifies the label for this agent. This label is publicized\
            (self-attested) to other agents as part of forming a connection.",
        )
        parser.add_argument(
            "--max-message-size",
            default=2097152,
            type=ByteSize(min_size=1024),
            metavar="<message-size>",
            help="Set the maximum size in bytes for inbound agent messages.",
        )

        parser.add_argument(
            "--enable-undelivered-queue",
            action="store_true",
            help="Enable the outbound undelivered queue that enables this agent to hold messages\
            for delivery to agents without an endpoint. This option will require\
            additional memory to store messages in the queue.",
        )

    def get_settings(self, args: Namespace):
        """Extract transport settings."""
        settings = {}
        settings["transport.inbound_configs"] = args.inbound_transports
        settings["transport.outbound_configs"] = args.outbound_transports
        settings["transport.enable_undelivered_queue"] = args.enable_undelivered_queue

        if args.endpoint:
            settings["default_endpoint"] = args.endpoint[0]
            settings["additional_endpoints"] = args.endpoint[1:]
        if args.label:
            settings["default_label"] = args.label
        if args.max_message_size:
            settings["transport.max_message_size"] = args.max_message_size

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
            help="Specifies the seed to use for the creation of a public DID\
            for the agent to use with a Hyperledger Indy ledger. The DID\
            must already exist on the ledger.",
        )
        parser.add_argument(
            "--wallet-key",
            type=str,
            metavar="<wallet-key>",
            help="Specifies the master key value to use for opening the wallet.",
        )
        parser.add_argument(
            "--wallet-name",
            type=str,
            metavar="<wallet-name>",
            help="Specifies the wallet name to be used by the agent.\
            This is useful if your deployment has multiple wallets.",
        )
        parser.add_argument(
            "--wallet-type",
            type=str,
            metavar="<wallet-type>",
            help="Specifies the type of Indy wallet provider to use.\
            Supported internal storage types are 'basic' (memory) and 'indy'.",
        )
        parser.add_argument(
            "--wallet-storage-type",
            type=str,
            metavar="<storage-type>",
            help="Specifies the type of Indy wallet backend to use.\
            Supported internal storage types are 'basic' (memory),\
            'indy', and 'postgres_storage'.",
        )
        parser.add_argument(
            "--wallet-storage-config",
            type=str,
            metavar="<storage-config>",
            help="Specifies the storage configuration to use for the wallet.\
            This is required if you are for using 'postgres_storage' wallet\
            storage type. For example, '{\"url\":\"localhost:5432\"}'.",
        )
        parser.add_argument(
            "--wallet-storage-creds",
            type=str,
            metavar="<storage-creds>",
            help="Specify the storage credentials to use for the wallet.\
            This is required if you are for using 'postgres_storage' wallet\
            For example, '{\"account\":\"postgres\",\"password\":\
            \"mysecretpassword\",\"admin_account\":\"postgres\",\"admin_password\":\
            \"mysecretpassword\"}'",
        )
        parser.add_argument(
            "--replace-public-did",
            action="store_true",
            help="If this parameter is set and an agent already has a public DID,\
            and the '--seed' parameter specifies a new DID, the agent will use\
            the new DID in place of the existing DID. Default: false.",
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
        if args.replace_public_did:
            settings["wallet.replace_public_did"] = True
        return settings
