"""Ledger configuration."""

from collections import OrderedDict
import logging
import re
import sys

import markdown
import prompt_toolkit
from prompt_toolkit.formatted_text import HTML

from ..ledger.base import BaseLedger

from .injection_context import InjectionContext

LOGGER = logging.getLogger(__name__)


async def ledger_config(
    context: InjectionContext, public_did: str, provision: bool = False
):
    """Perform Indy ledger configuration."""

    ledger: BaseLedger = await context.inject(BaseLedger, required=False)
    if not ledger or ledger.LEDGER_TYPE != "indy":
        LOGGER.info("Ledger not configured")
        return

    async with ledger:
        # Check transaction author agreement acceptance
        taa_info = await ledger.get_txn_author_agreement()
        if taa_info["taa_required"]:
            taa_accepted = await ledger.get_latest_txn_author_acceptance()
            if not taa_accepted or taa_info["taa_digest"] != taa_accepted["taaDigest"]:
                await accept_taa(ledger, taa_info, provision)

        # Publish endpoint if necessary
        endpoint = context.settings.get("default_endpoint")
        if public_did:
            await ledger.update_endpoint_for_did(public_did, endpoint)


async def accept_taa(ledger: BaseLedger, taa_info, provision: bool = False) -> bool:
    """Perform TAA acceptance."""

    if not sys.stdout.isatty():
        LOGGER.warning("Cannot accept TAA without interactive terminal")
        # return False

    mechanisms = taa_info["aml_record"]["aml"]
    allow_opts = OrderedDict(
        [
            (
                "wallet_agreement",
                "Store transaction author agreement acceptance in the wallet",
            ),
            (
                "on_file",
                "Acceptance of the transaction author agreement is on file in your organization",
            ),
        ]
    )
    if not provision:
        allow_opts[
            "for_session"
        ] = "Accept the transaction author agreement for the duration of the current session"

    found = []
    for opt in allow_opts:
        if opt in mechanisms:
            found.append(opt)

    md = markdown.Markdown()
    taa_html = md.convert(taa_info["taa_record"]["text"])
    taa_html = re.sub(
        r"<h[1-6]>(.*?)</h[1-6]>", r"<p><strong>\1</strong></p>\n", taa_html
    )
    taa_html = re.sub(r"<li>(.*?)</li>", r" - \1", taa_html)

    prompt_toolkit.print_formatted_text(HTML(taa_html))

    # tmp = await prompt_toolkit.prompt(*args, async_=True, **kwargs)

    mechanism = next(iter(found))
    await ledger.accept_txn_author_agreement(taa_info["taa_record"], mechanism)

    return True
