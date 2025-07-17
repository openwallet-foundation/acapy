# AnonCreds-RS Support

A new wallet type has been added to Aca-Py to support the new anoncreds-rs library:

```bash
--wallet-type askar-anoncreds
```

When Aca-Py is run with this wallet type it will run with an Askar format wallet (and askar libraries) but will use `anoncreds-rs` instead of `credx`.

There is a new package under `acapy_agent/anoncreds` with code that supports the new library.

There are new endpoints (under `/anoncreds`) for managing schemas, cred defs and revocation objects.  However the new anoncreds code is integrated into the existing Credential and Presentation endpoints (V2.0 endpoints only).

Within the protocols, there are new `handler` libraries to support the new `anoncreds` format (these are in parallel to the existing `indy` libraries).

The existing `indy` code are in:

```bash
acapy_agent/protocols/issue_credential/v2_0/formats/indy/handler.py
acapy_agent/protocols/indy/anoncreds/pres_exch_handler.py
acapy_agent/protocols/present_proof/v2_0/formats/indy/handler.py
```

The new `anoncreds` code is in:

```bash
acapy_agent/protocols/issue_credential/v2_0/formats/anoncreds/handler.py
acapy_agent/protocols/present_proof/anoncreds/pres_exch_handler.py
acapy_agent/protocols/present_proof/v2_0/formats/anoncreds/handler.py
```

The Indy handler checks to see if the wallet type is `askar-anoncreds` and if so delegates the calls to the anoncreds handler, for example:

```python
        # Temporary shim while the new anoncreds library integration is in progress
        wallet_type = profile.settings.get_value("wallet.type")
        if wallet_type == "askar-anoncreds":
            self.anoncreds_handler = AnonCredsPresExchangeHandler(profile)
```

... and then:

```python
        # Temporary shim while the new anoncreds library integration is in progress
        if self.anoncreds_handler:
            return self.anoncreds_handler.get_format_identifier(message_type)
```

To run the alice/faber demo using the new anoncreds library, start the demo with:

```bash
--wallet-type askar-anoncreds
```

There are no anoncreds-specific integration tests, for the new anoncreds functionality the agents within the integration tests are started with:

```bash
--wallet-type askar-anoncreds
```

Everything should just work!!!

Theoretically AATH should work with anoncreds as well, by setting the wallet type (see [https://github.com/openwallet-foundation/owl-agent-test-harness#extra-backchannel-specific-parameters](https://github.com/openwallet-foundation/owl-agent-test-harness#extra-backchannel-specific-parameters)).

## Revocation (new in anoncreds)

The changes are significant.  Notably:

- the old way was that from Indy you got the timestamp of the RevRegEntry used, accumulator and the "deltas" -- list of revoked and list of unrevoked credentials for a given range.  I'm not exactly sure what was passed to the AnonCreds library code for building the presentation.
- In the new way, the AnonCreds library expects the identifier for the revregentry used (aka the timestamp), the accumulator, and the full state (0s and 1s) of the revocation status of all credentials in the registry.
- The conversion from delta to full state must be handled in the Indy resolver -- not in the "generic" ACA-Py code, since the other ledgers automagically provide the full state. In fact, we're likely to update Indy VDR to always provide the full state.  The "common" (post resolver) code should get back from the resolver the full state.

The Tails File changes are minimal -- nothing about the file itself changed.  What changed:

- the tails-file-server can be published to WITHOUT knowing the ID of the RevRegEntry, since that is not known when the tails file is generated/published.  See: [https://github.com/bcgov/indy-tails-server/pull/53](https://github.com/bcgov/indy-tails-server/pull/53) -- basically, by publishing based on the hash.
- The tails-file is not needed by the issuer after generation. It used to be needed for issuing and revoking credentials. Those are now done without the tails file. See: [https://github.com/openwallet-foundation/acapy/pull/2302/files](https://github.com/openwallet-foundation/acapy/pull/2302/files). That code is already in Main, so you should have it.

## Outstanding work

- more testing - various scenarios like mediation, multitenancy etc.
- unit tests (review and possibly update unit tests for the credential and presentation integration)

## Retiring old Indy and Askar (credx) Code

The main changes for the Credential and Presentation support are in the following two files:

```bash
acapy_agent/protocols/issue_credential/v2_0/messages/cred_format.py
acapy_agent/protocols/present_proof/v2_0/messages/pres_format.py
```

The `INDY` handler just need to be re-pointed to the new anoncreds handler, and then all the old Indy code can be retired.

The new code is already in place (in comments).  For example for the Credential handler:

```python
        To make the switch from indy to anoncreds replace the above with the following
        INDY = FormatSpec(
            "hlindy/",
            DeferLoad(
                "acapy_agent.protocols.present_proof.v2_0"
                ".formats.anoncreds.handler.AnonCredsPresExchangeHandler"
            ),
        )
```

There is a bunch of duplicated code, i.e. the new anoncreds code was added either as new classes (as above) or as new methods within an existing class.

Some new methods were added within the Ledger class.

New unit tests were added - in some cases as methods within existing test classes, and in some cases as new classes (whichever was easiest at the time).
