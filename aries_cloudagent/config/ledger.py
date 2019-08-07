"""Ledger configuration."""

from collections import OrderedDict
import logging
import re
import sys

import markdown
import prompt_toolkit
from prompt_toolkit.eventloop.defaults import use_asyncio_event_loop
from prompt_toolkit.formatted_text import HTML

from ..ledger.base import BaseLedger

from .injection_context import InjectionContext

LOGGER = logging.getLogger(__name__)


async def ledger_config(
    context: InjectionContext, public_did: str, provision: bool = False
) -> bool:
    """Perform Indy ledger configuration."""

    ledger: BaseLedger = await context.inject(BaseLedger, required=False)
    if not ledger:
        LOGGER.info("Ledger instance not provided")
        return False
    elif ledger.LEDGER_TYPE != "indy":
        LOGGER.info("Non-indy ledger provided")
        return False

    async with ledger:
        # Check transaction author agreement acceptance
        taa_info = await ledger.get_txn_author_agreement()
        if taa_info["taa_required"] and public_did:
            taa_accepted = await ledger.get_latest_txn_author_acceptance()
            if not taa_accepted or taa_info["taa_digest"] != taa_accepted["taaDigest"]:
                if not await accept_taa(ledger, taa_info, provision):
                    return False

        # Publish endpoint if necessary - skipped if TAA is required but not accepted
        endpoint = context.settings.get("default_endpoint")
        if public_did:
            await ledger.update_endpoint_for_did(public_did, endpoint)

    return True


async def accept_taa(ledger: BaseLedger, taa_info, provision: bool = False) -> bool:
    """Perform TAA acceptance."""

    if not sys.stdout.isatty():
        LOGGER.warning("Cannot accept TAA without interactive terminal")
        return False

    mechanisms = taa_info["aml_record"]["aml"]
    allow_opts = OrderedDict(
        [
            (
                "wallet_agreement",
                (
                    "Accept the transaction author agreement and store the "
                    + "acceptance in the wallet"
                ),
            ),
            (
                "on_file",
                (
                    "Acceptance of the transaction author agreement is on file "
                    + "in my organization"
                ),
            ),
        ]
    )
    if not provision:
        allow_opts["for_session"] = (
            "Accept the transaction author agreement for the duration of "
            + "the current session"
        )

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

    taa_html = (
        "\n<strong>Transaction Author Agreement version "
        + taa_info["taa_record"]["version"]
        + "</strong>\n\n"
        + taa_html
    )

    # setup for prompt_toolkit
    use_asyncio_event_loop()

    prompt_toolkit.print_formatted_text(HTML(taa_html))

    opts = []
    num_mechanisms = {}
    for idx, opt in enumerate(found):
        num_mechanisms[str(idx + 1)] = opt
        opts.append(f" {idx+1}. {allow_opts[opt]}")
    opts.append(" X. Skip the transaction author agreement")
    opts_text = "\nPlease select an option:\n" + "\n".join(opts) + "\n[1]> "

    while True:
        try:
            opt = await prompt_toolkit.prompt(opts_text, async_=True)
        except EOFError:
            return False
        if not opt:
            opt = "1"
        opt = opt.strip()
        if opt in ("x", "X"):
            return False
        if opt in num_mechanisms:
            mechanism = num_mechanisms[opt]
            break

    await ledger.accept_txn_author_agreement(taa_info["taa_record"], mechanism)

    return True
