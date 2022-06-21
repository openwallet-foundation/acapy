# Troubleshooting Aries Cloud Agent Python <!-- omit in toc -->

This document contains some troubleshooting information that contributors to the
community think may be helpful. Most of the content here assumes the reader has
gotten started with ACA-Py and has arrived here because of an issue that came up
in their use of ACA-Py.

Contributions (via pull request) to this document are welcome. Topics added here
will mostly come from reported issues that contributors think would be helpful
to the larger community.

## Table of Contents <!-- omit in toc -->

- [Unable to Connect to Ledger](#unable-to-connect-to-ledger)
  - [Local ledger running?](#local-ledger-running)
  - [Any Firewalls](#any-firewalls)
- [Damaged, Unpublishable Revocation Registry](#damaged-unpublishable-revocation-registry)

## Unable to Connect to Ledger

The most common issue hit by first time users is getting an error on startup "unable to connect to ledger". Here are a list of things to check when you see that error.

### Local ledger running?

Unless you specify via startup parameters or environment variables that you are using a public Hyperledger Indy ledger, ACA-Py assumes that you are running a local ledger -- an instance of [von-network](https://github.com/bcgov/von-network).
If that is the cause -- have you started your local ledger, and did it startup properly.  Things to check:

- Any errors in the startup of von-network?
- Is the von-network webserver (usually at `https:/localhost:9000`) accessible? If so, can you click on and see the Genesis File?
- Do you even need a local ledger? If not, you can use a public sandbox ledger,
  such as the [Dev Greenlight ledger](), likely by just prefacing your ACA-Py
  command with `LEDGER_URL=http://dev.greenlight.bcovrin.vonx.io`. For example,
  when running the Alice-Faber demo in the [demo](demo) folder, you can run (for
  example), the Faber agent using the command:
  `LEDGER_URL=http://dev.greenlight.bcovrin.vonx.io ./run_demo faber`

### Any Firewalls

Do you have any firewalls in play that might be blocking the ports that are used by the ledger, notably 9701-9708? To access a ledger
the ACA-Py instance must be able to get to those ports of the ledger, regardless if the ledger is local or remote.

## Damaged, Unpublishable Revocation Registry

We have discovered that in the ACA-Py AnonCreds implementation, it is possible
to get into a state where the publishing of updates to a Revocation Registry
(RevReg) is impossible. This can happen where ACA-Py starts to publish an update
to the RevReg, but the write transaction to the Hyperledger Indy ledger fails
for some reason. When a credential revocation is published, aca-py (via indy-sdk
or askar/credx) updates the revocation state in the wallet as well as on the
ledger.  The revocation state is dependant on whatever the previous revocation
state is/was, so if the ledger and wallet are mis-matched the publish will fail.
(Andrew/s PR # 1804 (merged) should mitigate but probably won't completely
eliminate this from happening).

For example, in case we've seen, the write RevRegEntry transaction failed at the
ledger because there was a problem with accepting the TAA (Transaction Author
Agreement). Once the error occurred, the RevReg state held by the ACA-Py agent,
and the RevReg state on the ledger were different. Even after the ability to
write to the ledger was restored, the RevReg could still not be published
because of the differences in the RevReg state. Such a situation can now be
corrected, as follows:

To address this issue, some new endpoints were added to ACA-Py in Release 0.7.4,
as follows:

- GET `/revocation/registry/<id>/issued` - counts of the number of issued/revoked
  within a registry
- GET `/revocation/registry/<id>/issued/details` - details of all credentials
  issued/revoked within a registry
- GET `/revocation/registry/<id>/issued/indy_recs` - calculated rev_reg_delta from
  the ledger
  - This is used to compare ledger revoked vs wallet revoked credentials, which
    is essentially the state of the RevReg on the ledger and in ACA-Py. Where
    there is a difference, we have an error.
- PUT `/revocation/registry/<id>/fix-revocation-entry-state` - publish an update
  to the RevReg state on the ledger to bring it into alignment with what is in
  the ACA-Py instance.
  - There is a boolean parameter (`apply_ledger_update`) to control whether the
    ledger entry actually gets published so, if you are so inclined, you can
    call the endpoint to see what the transaction would be, before you actually
    try to do a ledger update.  This will return:
    - `rev_reg_delta` - same as the ".../indy_recs" endpoint
    - `accum_calculated` - transaction to write to ledger
    - `accum_fixed` - If `apply_ledger_update`, the transaction actually written
      to the ledger

Note that there is (currently) a backlog item to prevent the wallet and ledger
from getting out of sync (e.g. don't update the ACA-Py RevReg state if the
ledger write fails), but even after that change is made, having this ability
will be retained for use if needed.

We originally ran into this due to the TAA acceptance getting lost when
switching to multi-ledger (as described
[here](https://github.com/hyperledger/aries-cloudagent-python/blob/main/Multiledger.md#a-special-warning-for-taa-acceptance).
Note that this is one reason how this "out of sync" scenario can occur, but
there may be others.

We add an integration test that demonstrates/tests this issue [here](https://github.com/hyperledger/aries-cloudagent-python/blob/main/demo/features/taa-txn-author-acceptance.feature#L67).

To run the scenario either manually or using the integration tests, you can do the following:

- Start von-network in TAA mode:
  - `./manage start --taa-sample --logs`
- Start the tails server as usual:
  - `./manage start --logs`
- To run the scenario manually, start faber and let the agent know it needs to TAA-accept before doing any ledger writes:
  - `./run_demo faber --revocation --taa-accept`, and then you can run through all the transactions using the Swagger page.
- To run the scenario via an integration test, run:
  - `./run_bdd -t @taa_required`
