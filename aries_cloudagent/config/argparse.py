"""Command line option parsing."""

import os
import argparse
from typing import Sequence

from .error import ArgsParseError

PARSER = argparse.ArgumentParser(description="Runs an Aries Cloud Agent.")


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
    "--log-config",
    dest="log_config",
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
    + 'e.g., \'{"account":"postgres","password":"mysecretpassword",'
    + '"admin_account":"postgres","admin_password":"mysecretpassword"}\'',
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

PARSER.add_argument(
    "--admin-api-key",
    type=str,
    metavar="<api-key>",
    help="Set the api key for the admin API.",
)

PARSER.add_argument(
    "--admin-insecure-mode",
    action="store_true",
    help="Do not protect the admin API with token authentication.z",
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

PARSER.add_argument(
    "--webhook-url",
    action="append",
    metavar="<url>",
    help="Send webhooks to a given URL",
)


def parse_args(args: Sequence[str] = None):
    """Parse command line arguments and return the collection."""
    return PARSER.parse_args(args)


def get_settings(args):
    """Convert command line arguments to a settings dictionary."""
    settings = {}

    if args.log_config:
        settings["log.config"] = args.log_config
    if args.log_level:
        settings["log.level"] = args.log_level

    settings["transport.inbound_configs"] = args.inbound_transports
    settings["transport.outbound_configs"] = args.outbound_transports

    if args.endpoint:
        settings["default_endpoint"] = args.endpoint
    if args.label:
        settings["default_label"] = args.label

    if args.genesis_url:
        settings["ledger.genesis_url"] = args.genesis_url
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
    if args.wallet_storage_config:
        settings["wallet.storage_config"] = args.wallet_storage_config
    if args.wallet_storage_creds:
        settings["wallet.storage_creds"] = args.wallet_storage_creds

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

    if args.debug:
        settings["debug.enabled"] = True
    if args.debug_connections:
        settings["debug.connections"] = True
    if args.debug_seed:
        settings["debug.seed"] = args.debug_seed
    if args.invite:
        settings["debug.print_invitation"] = True

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

    return settings
