# Upgrading ACA-Py Data

Some releases of ACA-Py may be improved by, or even require, an upgrade when
moving to a new version. Such changes are documented in the [CHANGELOG.md],
and those with ACA-Py deployments should take note of those upgrades. This
document summarizes the upgrade system in ACA-Py.

## Version Information and Automatic Upgrades

The file [version.py] contains the current version of a running instance of
ACA-Py. In addition, a record is made in the ACA-Py secure storage (database)
about the "most recently upgraded" version. When deploying a new version of
ACA-Py, the [version.py] value will be higher than the version in
secure storage. When that happens, an upgrade is executed, and on successful
completion, the version is updated in secure storage to match what is
in [version.py].

Upgrades are defined in the [Upgrade Definition YML file]. For a given
version listed in the follow, the corresponding entry is what actions are
required when upgrading from a previous version. If a version is not listed
in the file, there is no upgrade defined for that version from its immediate
predecessor version.

Once an upgrade is identified as needed, the process is:

- Collect (if any) the actions to be taken to get from the version recorded in
secure storage to the current [version.py]
- Execute the actions from oldest to newest.
    - If the same action is collected more than once (e.g., "Resave the
Connection Records" is defined for two different versions), perform the action
only once.
- Store the current ACA-Py version (from [version.py]) in the secure storage
  database.

## Forced Offline Upgrades

In some cases, it may be necessary to do an offline upgrade, where ACA-Py is
taken off line temporarily, the database upgraded explicitly, and then
ACA-Py re-deployed as normal. As yet, we do not have any use cases for this, but
those deploying ACA-Py should be aware of this possibility. For example,
we may at some point need an upgrade that **MUST NOT** be executed by more
than one ACA-Py instance. In that case, a "normal" upgrade could be dangerous
for deployments on container orchestration platforms like Kubernetes.

If the Maintainers of ACA-Py recognize a case where ACA-Py must be upgraded
while offline, a new Upgrade feature will be added that will prevent the "auto
upgrade" process from executing. See [Issue 2201] and [Pull Request 2204] for
the status of that feature.

[Issue 2201]: https://github.com/hyperledger/aries-cloudagent-python/issues/2201
[Pull Request 2204]: https://github.com/hyperledger/aries-cloudagent-python/pull/2204

Those deploying ACA-Py upgrades for production installations (forced offline or
not) should check in each [CHANGELOG.md] release entry about what upgrades (if
any) will be run when upgrading to that version, and consider how they want
those upgrades to run in their ACA-Py installation. In most cases, simply
deploying the new version should be OK. If the number of records to be upgraded
is high (such as a "resave connections" upgrade to a deployment with many, many
connections), you may want to do a test upgrade offline first, to see if there
is likely to be a service disruption during the upgrade. Plan accordingly!

## Exceptions

There are a couple of upgrade exception conditions to consider, as outlined
in the following sections.

### No version in secure storage

Versions prior to ACA-Py 0.8.1 did not automatically populate the secure storage
"version" record. That only occurred if an upgrade was explicitly executed. As
of ACA-Py 0.8.1, the version record is added immediately after the secure
storage database is created. If you are upgrading to ACA-Py 0.8.1 or later, and
there is no version record in the secure storage, ACA-Py will assume you are
running version 0.7.5, and execute the upgrades from version 0.7.5 to the
current version. The choice of 0.7.5 as the default is safe because the same
upgrades will be run on any version of ACA-Py up to and including 0.7.5, as can
be seen in the [Upgrade Definition YML file]. Thus, even if you are really
upgrading from (for example) 0.6.2, the same upgrades are needed as from 0.7.5
to a post-0.8.1 version.

### Forcing an upgrade

If you need to force an upgrade from a given version of ACA-Py, a pair of
configuration options can be used together. If you specify "`--from-version
<ver>`" and "`--force-upgrade`", the `--from-version` version will override what
is found (or not) in secure storage, and the upgrade will be from that version
to the current one. For example, if you have "0.8.1" in your "secure storage"
version, and you know that the upgrade for version 0.8.1 has not been executed,
you can use the parameters `--from-version v0.7.5 --force-upgrade` to force the
upgrade on next starting an ACA-Py instance. However, given the few upgrades
defined prior to version 0.8.1, and the "[no version in secure
storage](#no-version-in-secure-storage)" handling, it is unlikely this
capability will ever be needed. We expect to deprecate and remove these
options in future (post-0.8.1) ACA-Py versions.

[CHANGELOG.md]: https://github.com/hyperledger/aries-cloudagent-python/blob/main/CHANGELOG.md
[version.py]: https://github.com/hyperledger/aries-cloudagent-python/blob/main/aries_cloudagent/version.py
[Upgrade Definition YML file]: https://github.com/hyperledger/aries-cloudagent-python/blob/main/aries_cloudagent/commands/default_version_upgrade_config.yml