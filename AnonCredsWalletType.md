# AnonCreds-Rs Support

A new wallet type has been added to Aca-Py to support the new anoncreds-rs library:

```
--wallet-type askar-anoncreds
```

When Aca-Py is run with this wallet type it will run with an Askar format wallet (and askar libraries) but will use `anoncreds-rs` instead of `credx`.

There is a new package under `aries_cloudagent/anoncreds` with code that supports the new library.

There are new endpoints (under `/anoncreds`) for creating a Schema and Credential Definition.  However the new anoncreds code is integrated into the existing Credential and Presentation endpoints (V2.0 endpoints only).

Within the protocols, there are new `handler` libraries to support the new `anoncreds` format (these are in parallel to the existing `indy` libraries).

The existing `indy` code are in:

```
aries_cloudagent/protocols/issue_credential/v2_0/formats/indy/handler.py
aries_cloudagent/protocols/indy/anoncreds/pres_exch_handler.py
aries_cloudagent/protocols/present_proof/v2_0/formats/indy/handler.py
```

The new `anoncreds` code is in:

```
aries_cloudagent/protocols/issue_credential/v2_0/formats/anoncreds/handler.py
aries_cloudagent/protocols/present_proof/anoncreds/pres_exch_handler.py
aries_cloudagent/protocols/present_proof/v2_0/formats/anoncreds/handler.py
```

The Indy handler checks to see if the wallet type is `askar-anoncreds` and if so delegates the calls to the anoncreds handler, for example:

```
        # Temporary shim while the new anoncreds library integration is in progress
        wallet_type = profile.settings.get_value("wallet.type")
        if wallet_type == "askar-anoncreds":
            self.anoncreds_handler = AnonCredsPresExchangeHandler(profile)
```

... and then:

```
        # Temporary shim while the new anoncreds library integration is in progress
        if self.anoncreds_handler:
            return self.anoncreds_handler.get_format_identifier(message_type)
```

To run the alice/faber demo using the new anoncreds library, start the demo with:

```
--wallet-type askar-anoncreds
```

There are no anoncreds-specific integration tests, for the new anoncreds functionality the agents within the integration tests are started with:

```
--wallet-type askar-anoncreds
```

Everything should just work!!!

Theoretically ATH should work with anoncreds as well, by setting the wallet type (see https://github.com/hyperledger/aries-agent-test-harness#extra-backchannel-specific-parameters).

## Outstanding work

- unit tests (in the new anoncreds package)
- unit tests (review and possibly update unit tests for the credential and presentation integration)
- revocation support - migrate code from `anoncreds-rs` branch
- revocation support - complete the revocation implementation (support for unhappy path scenarios)
- endorsement (not implemented with new anoncreds code)
- testing - various scenarios like mediation, multitenancy etc.
- wallet upgrade (askar to askar-anoncreds)
- update V1.0 versions of the Credential and Presentation endpoints to use anoncreds
- any other anoncreds issues - https://github.com/hyperledger/aries-cloudagent-python/issues?q=is%3Aopen+is%3Aissue+label%3AAnonCreds

## Retiring old Indy and Askar (credx) Code

The main changes for the Credential and Presentation support are in the following two files:

```
aries_cloudagent/protocols/issue_credential/v2_0/messages/cred_format.py
aries_cloudagent/protocols/present_proof/v2_0/messages/pres_format.py
```

The `INDY` handler just need to be re-pointed to the new anoncreds handler, and then all the old Indy code can be retired.

The new code is already in place (in comments).  For example for the Credential handler:

```
        To make the switch from indy to anoncreds replace the above with the following
        INDY = FormatSpec(
            "hlindy/",
            DeferLoad(
                "aries_cloudagent.protocols.present_proof.v2_0"
                ".formats.anoncreds.handler.AnonCredsPresExchangeHandler"
            ),
        )
```

There is a bunch of duplicated code, i.e. the new anoncreds code was added either as new classes (as above) or as new methods within an existing class.

Some new methods were added within the Ledger class.

New unit tests were added - in some cases as methods within existing test classes, and in some cases as new classes (whichever was easiest at the time).
