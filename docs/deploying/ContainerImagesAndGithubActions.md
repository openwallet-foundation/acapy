# Container Images and Github Actions

ACA-Py is most frequently deployed using containers. From
the first release of ACA-Py up through 0.7.4, much of the community has built
their deployments using the container images graciously provided by BC Gov and
hosted through their `bcgovimages` docker hub account. These images have been
critical to the adoption of not only ACA-Py but also decentralized trust/SSI
more generally.

Recognizing how critical these images are to the success of ACA-Py and
consistent with the OpenWallet Foundation's commitment to open collaboration, container images
are now built and published directly from the Aries Cloud Agent - Python project
repository and made available through the [Github Packages Container
Registry](https://ghcr.io).

## Image

This project builds and publishes the `ghcr.io/openwallet-foundation/acapy-agent` image.
Multiple variants are available; see [Tags](#tags).

### Tags

ACA-Py is a foundation for building decentralized identity applications; to this
end, there are multiple variants of ACA-Py built to suit the needs of a variety
of environments and workflows. The following variants exist:

- "Standard" - The default configuration of ACA-Py, including:
  - Aries Askar for secure storage
  - Indy VDR for Indy ledger communication
  - AnonCreds Rust for AnonCreds

In the past, two image variants were published. These two variants are largely
distinguished by providers for Indy Network and AnonCreds support. The Standard
variant is recommended for new projects. Migration from an Indy based image
(whether the new Indy image variant or the original BC Gov images) to the
Standard image is outside of the scope of this document.

The ACA-Py images built by this project are tagged to indicate which of the
above variants it is. Other tags may also be generated for use by developers.

Click [here](https://github.com/openwallet-foundation/acapy/pkgs/container/acapy-agent/versions?filters%5Bversion_type%5D=tagged) to see a current list of the tagged images available for ACA-Py in.

The following is the ACA-Py comntainer images tagging format. In each of the following, `pyV.vv` is the base Python image being used (e.g. `py3.12`):

- Regular Releases: `pyV.vv-X.Y.Z` where `X.Y.Z` is the ACA-Py release.  The `Z` component may have an `rcN` appended when the tag is for a Release Candidate.
- Nightlies: `pyV-vv-nightly-YYYY-MM-DD` and `pyV-vv-nightly`
- LTS ([Long Term Support](../LTS-Strategy.md)): `pyV-vv-X.Y-lts`, where the `X.Y` are the major and minor components of the LTS (e.g. `0.12`, `1.2`). This tag moves to always be on latest release of each line of LTS releases (e.g. from `0.12.4` to `0.12.5` when the latter is released).

### Image Comparison

There are several key differences that should be noted between the two image
variants and between the BC Gov ACA-Py images.

- Standard Image
  - Based on slim variant of Debian
  - Does **NOT** include `libindy`
  - Default user is `aries`
  - Uses container's system python environment rather than `pyenv`
  - Askar and Indy Shared libraries are installed as dependencies of ACA-Py through pip from pre-compiled binaries included in the python wrappers
  - Built from repo contents
- Indy Image (no longer produced but included here for clarity)
  - Based on slim variant of Debian
  - Built from multi-stage build step (`indy-base` in the Dockerfile) which includes Indy dependencies; this could be replaced with an explicit `indy-python` image from the Indy SDK repo
  - Includes `libindy` but does **NOT** include the Indy CLI
  - Default user is `indy`
  - Uses container's system python environment rather than `pyenv`
  - Askar and Indy Shared libraries are installed as dependencies of ACA-Py through pip from pre-compiled binaries included in the python wrappers
  - Built from repo contents
  - Includes Indy postgres storage plugin

## Github Actions

- Tests (`.github/workflows/tests.yml`) - A reusable workflow that runs tests
  for the Standard ACA-Py variant for a given python version.
- PR Tests (`.github/workflows/pr-tests.yml`) - Run on pull requests; runs tests
  for the Standard ACA-Py variant for a "default" python version.
  Check this workflow for the current default python version in use.
- Nightly Tests (`.github/workflows/nightly-tests.yml`) - Run nightly; runs
  tests for the Standard ACA-Py variant for all currently supported
  python versions. Check this workflow for the set of currently supported
  versions in use.
- Publish (`.github/workflows/publish.yml`) - Run on new release published or
  when manually triggered; builds and pushes the Standard ACA-Py variant to the
  Github Container Registry.
- BDD Integration Tests (`.github/workflows/BDDTests.yml`) - Run on pull
  requests (to the openwallet-foundation fork only); runs BDD integration tests.
- Format (`.github/workflows/format.yml`) - Run on pull requests;
  checks formatting of files modified by the PR.
- CodeQL (`.github/workflows/codeql.yml`) - Run on pull requests; performs
  CodeQL analysis.
- Python Publish (`.github/workflows/pythonpublish.yml`) - Run on release
  created; publishes ACA-Py python package to PyPI.
- PIP Audit (`.github/workflows/pipaudit.yml`) - Run when manually triggered;
  performs pip audit.
