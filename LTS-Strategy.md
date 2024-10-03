# ACA-Py LTS Strategy

This document defines the Long-term support (LTS) release strategy for ACA-Py. This document is inspired from the [Hyperledger Fabric Release Strategy](https://github.com/hyperledger/fabric-rfcs/blob/main/text/0005-lts-release-strategy.md). 

Long-term support definition from wikipedia.org:

> **Long-term support (LTS)** is a product lifecycle management policy in which a stable release of computer software is maintained for a longer period of time than the standard edition.

> **LTS** applies the tenets of reliability engineering to the software development process and software release life cycle. Long-term support extends the period of software maintenance; it also alters the type and frequency of software updates (patches) to reduce the risk, expense, and disruption of software deployment, while promoting the dependability of the software.

## Motivation

Many of those using ACA-Py rely upon the [Docker images](https://github.com/openwallet-foundation/acapy/pkgs/container/acapy-agent) which are published nightly and the [releases](https://github.com/openwallet-foundation/acapy/releases). These images contain the project dependencies/libraries which need constant security vulnerability monitoring and patching.

This is one of the factors which motivated setting up the LTS releases which requires the docker images to be scanned regularly and patching them for vulnerabilities.

In addition to this, administrators can expect the following of a LTS release:

- Stable and well-tested code
- A list of supported RFCs and features for each LTS version from this [document](https://github.com/openwallet-foundation/acapy/blob/main/docs/features/SupportedRFCs.md).
- Minimal set of feature additions and other changes that can easily be applied, reducing the risk of functional regressions and bugs

Similarly, there are benefits to ACA-Py maintainers, code contributors, and the wider community:

- New features and other changes can quickly be applied to the main branch, and distributed to the user community for trial, without impacting production deployments.
- Community feedback on new features can be solicited and acted upon.
- Bug fixes only need to be backported to a small number of designated LTS releases.
- Extra tests (e.g. upgrade tests for non-subsequent versions) only need to be executed against a small number of designated LTS releases.

## ACA-Py LTS Mechanics

### Versioning

ACA-Py uses the [semver](https://semver.org/) pattern of major, minor and patch releases `major.minor.patch` e.g. 0.10.5, 0.11.1, 0.12.0, 0.12.1, 1.0.0, 1.0.1 etc. Prior to the 1.0.0 release of ACA-Py, "major" releases triggered only a "minor" version update, as permitted by the [semver]() handling of the `0` major version indicator.

### LTS Release Cadence

Because a new major release typically has large new features that may not yet be tried by the user community, and because deployments may lag in support of the new release, it is not expected that a new major release (such as `1.0.0`) will immediately be designated as a LTS release. Eventually, each major release (0.x.x, 1.x.x, 2.x.x etc.) will have at least one minor release designated by the ACA-Py maintainers as an "LTS release."

After an LTS release is designated, succeeding patch releases will occur as normal. When the ACA_Py maintainers decide that a new major or minor release is required, an "LTS" git branch for the most recent patch of the LTS line will be created -- likely named `<minor>.lts` (e.g., `0.11.lts`, `1.1.lts`). Subsequent patches to that designated LTS release will occur from that branch -- often cherry-picked from the `main` branch. There is no predefined timing for next minor/major version, with the decision based on semantic versioning considerations, such as whether API changes are needed, or deprecated capabilities need to be removed. Other considerations may also apply, for example significant upgrade steps may motivate a shift to a new major version.

If a major release is not delivered for an extended period of time, the maintainers may designate a later minor release as the next LTS release, for example if `1.1` is the latest LTS release and there is no need to increment to `2.0` for several quarters, the maintainers may decide to designate `1.3` as an LTS release.

### LTS 3rd Digit Patch Releases

For LTS releases, 3rd digit patch releases will be provided for bug and security fixes approximately every three months based on the fixes (or lack thereof) to be applied. In order to ensure the stability of the LTS release and reduce the risk of functional regressions and bugs, significant new features and other changes occurring on the `main` branch, and released in later minor or major versions will not be included in LTS patch releases.

### LTS Release Duration

When a *new* LTS release is designated, an "end-of-life" date will be set as being **9 months** later for the *prior* LTS release. The overlap period is intended to provide users a time window to upgrade their deployments. Users can expect LTS patch releases to address critical bugs and other fixes through that end-of-life date. If there are multiple, active LTS branches, ACA-Py maintainers will determine which fixes are backported to which of those branches.

### LTS to LTS Compatibility

Features related to ACA-Py capabilities are documented in the [Supported RFCs and features](https://github.com/openwallet-foundation/acapy/blob/main/docs/features/SupportedRFCs.md), in the ACA-Py [ChangeLog](https://github.com/openwallet-foundation/acapy/blob/main/CHANGELOG.md), and in documents updated and added as part of each ACA-Py Release. LTS to LTS compatibility can be determined from reviewing those sources.

### Upgrade Testing

The ACA-Py project expects to test and provide guidance on all major/minor upgrades (e.g. 0.11 to 0.12). Other upgrade paths will not be tested and are not guaranteed to work. Consult the [ChangeLog](https://github.com/openwallet-foundation/acapy/blob/main/CHANGELOG.md) and its pointers to release-to-release upgrade information for guidance.

## Prior art and alternatives

While many open source projects provide LTS releases, there is no industry standard for LTS release approach. Projects use many different variants of LTS approaches to best suit their project's particular needs.

This release strategy was based on the following open source projects:

- [Hyperledger Fabric](https://github.com/hyperledger/fabric-rfcs/blob/main/text/0005-lts-release-strategy.md)
- [NodeJS](https://nodejs.org/en/about/previous-releases)
