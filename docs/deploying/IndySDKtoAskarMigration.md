# Migrating from Indy SDK to Askar

The document summarizes why the [Indy SDK] is being deprecated, it's replacement
([Aries Askar] and the "shared components"), how to use [Aries Askar in a new
ACA-Py deployment](#new-aca-py-deployments), and the [migration
process](#migrating-existing-indy-sdk-aca-py-deployments-to-askar) for an ACA-Py
instance that is already deployed using the Indy SDK.

## The Time Has Come! Archiving Indy SDK

Yes, it’s time. Indy SDK needs to be archived! In this article we’ll explain why
this change is needed, why Aries Askar is a faster, better replacement, and how
to transition your Indy SDK-based ACA-Py deployment to Askar as soon as
possible.

[Indy SDK]: https://github.com/hyperledger/indy-sdk
[Aries Askar]: https://github.com/hyperledger/aries-askar

### History of Indy SDK

Indy SDK has been the basis of [Hyperledger Indy] and [Hyperledger Aries] clients
accessing Indy networks for a long time. It has done an excellent job at exactly
what you might imagine: being the SDK that enables clients to leverage the
capabilities of a Hyperledger Indy ledger.

Its continued use has been all the more remarkable given that the last published
release of the Indy SDK was in 2020. This speaks to the **quality of the
implementation** — it just kept getting used, doing what it was supposed to do,
and without major bugs, vulnerabilities or demands for new features.

However, the architecture of Indy SDK has **critical bottlenecks**. Most
notably, as load increases, Indy SDK performance drops. And with Indy-based
ecosystems flourishing and loads exponentially increasing, this means the
Aries/Indy community needed to make a change.

[Hyperledger Indy]: https://www.hyperledger.org/projects/hyperledger-indy
[Hyperledger Aries]: https://www.hyperledger.org/projects/aries

### Aries Askar and the Shared Components

The replacement for the Indy SDK is a set of **four components**, each replacing
a part of Indy SDK. (In retrospect, Indy SDK ought to have been split up this
way from the start.)

The components are:

1. **[Aries Askar]**: the replacement for the “indy-wallet” part of Indy SDK.
   Askar is a key management service, handling the creation and use of private
   keys managed by Aries agents. It’s also the secure storage for DIDs,
   verifiable credentials, and data used by issuers of verifiable credentials
   for signing. As the Aries moniker indicates, Askar is suitable for use with
   any Aries agent, and for managing any keys, whether for use with Indy or any
   other Verifiable Data Registry (VDR).
2. **[Indy VDR]**: the interface to publishing to and retrieving data from
   Hyperledger Indy networks. Indy VDR is scoped at the appropriate level for
   any client application using Hyperledger Indy networks.
3. **[CredX]**: a Rust implementation of AnonCreds that evolved from the Indy
   SDK implementation. CredX is within the [indy-shared-rs] repository. It has
   significant performance enhancements over the version in the Indy SDK,
   particularly for Issuers.
4. **[Hyperledger AnonCreds]**: a newer implementation of AnonCreds that is
   “ledger-agnostic” — it can be used with Hyperledger Indy and any other
   suitable verifiable data registry.

In ACA-Py, we are currently using CredX, but will be moving to Hyperledger
AnonCreds soon.

[Indy VDR]: https://github.com/hyperledger/indy-vdr
[CredX]: https://github.com/hyperledger/indy-shared-rs
[indy-shared-rs]: https://github.com/hyperledger/indy-shared-rs
[Hyperledger AnonCreds]: https://github.com/hyperledger/anoncreds-rs

If you’re involved in the community, you’ll know we’ve been planning this
replacement for almost three years. The first release of the Aries Askar and
related components was in 2021. At the end of 2022 there was a concerted effort
to eliminate the Indy SDK by creating migration scripts, and removing the Indy
SDK from various tools in the community (the Indy CLI, the Indy Test Automation
pipeline, and so on). This step is to finish the task.

### Performance

What’s the performance and stability of the replacement? In short, it’s
**dramatically better**. Overall Aries Askar performance is faster, and as the
load increases the performance remains constant. Combined with added flexibility
and modularization, the community is very positive about the change.

## New ACA-Py Deployments

If you are new to ACA-Py, the instructions are easy. Use Aries Askar and the
shared components from the start. To do that, simply make sure that you are
using the `--wallet-type askar` configuration parameter. You will automatically
be using all of the shared components.

As of release 0.9.0, you will get a deprecation warning when you start ACA-Py
with the Indy SDK. Switch to Aries Askar to eliminate that warning.

## Migrating Existing Indy SDK ACA-Py Deployments to Askar

If you have an existing deployment, in changing the `--wallet-type`
configuration setting, your database must be migrated from the Indy SDK format
to Aries Askar format. In order to facilitate the migration, an Indy SDK to
Askar migration script has been published in the [aries-acapy-tools] repository.
There is lots of information in that repository about the migration tool and how
to use it. The following is a summary of the steps you will have to perform. Of
course, all deployments are a little (or a lot!) different, and your exact steps
will be dependent on where and how you have deployed ACA-Py.

[aries-acapy-tools]: https://github.com/hyperledger/aries-acapy-tools

Note that in these steps you will have to take your ACA-Py instance offline, so
scheduling the maintenance must be a part of your migration plan. You will also
want to script the entire process so that downtime and risk of manual mistakes
are minimized.

We hope that you have one or two test environments (e.g., Dev and Test) to run
through these steps before upgrading your production deployment. As well, it is
good if you can make a copy of your production database and test the migration
on the real (copy) database before the actual upgrade.

* Prepare a way to run the Askar Upgrade script from the [aries-acapy-tools]
  repository. For example, you might want to prepare a container that you can
  run in the same environment that you run ACA-Py (e.g., within Kubernetes or
  OpenShift).
* Shutdown your ACA-Py instance.
* Backup the existing wallet using the usual tools you have for backing up the
  database.
* If you are running in a cloud native environment such as Kubernetes, deploy
  the Askar Upgrade container, and as needed, update the network policies to
  allow the Askar Upgrade container to connect with the wallet database
* Run the `askar-upgrade` script. For example:

``` bash
askar-upgrade \
  --strategy dbpw \
  --uri postgres://<username>:<password>@<hostname>:<port>/<dbname> \
  --wallet-name <wallet name> \
  --wallet-key <wallet key>
```

* Switch the ACA-Py instance's `--wallet-type` configuration setting to `askar`
* Start up the ACA-Py instances.
  * Trouble? Restore the initial database and revert the `--wallet-type` change
    to rollback to the pre-migration state.
* Check the data.
* Test the deployment.

It is very important that the Askar Upgrade script has direct access to the
database. In our very first upgrade attempt, we ran the Upgrade Askar script
from a container running outside of our container orchestration platform
(OpenShift) using port forwarding. The script ran EXTREMELY slowly, taking
literally hours to run before we finally stopped it. Once we ran the script
inside the OpenShift environment, the script ran (for the same database) in
about 7 minutes. The entire app downtime was less than 20 minutes.

## Questions?

If you have questions, comments, or suggestions about the upgrade process,
please use the Aries Cloud Agent Python channel on [Hyperledger Discord], or
submit a [GitHub issue to the ACA-Py repository].

[Hyperledger Discord]: https://discord.gg/hyperledger
[GitHub issue to the ACA-Py repository]: https://github.com/hyperledger/aries-cloudagent-python/issues
