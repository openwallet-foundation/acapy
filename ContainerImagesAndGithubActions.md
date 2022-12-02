# Container Images and Github Actions

Aries Cloud Agent - Python is most frequently deployed using containers. From
the first release of ACA-Py up through 0.7.4, much of the community has built
their Aries stack using the container images graciously provided by BC Gov and
hosted through their `bcgovimages` docker hub account. These images have been
critical to the adoption of not only ACA-Py but also Hyperledger Aries and SSI
more generally.

Recognizing how critical these images are to the success of ACA-Py and
consistent with Hyperledger's commitment to open collaboration, container images
are now built and published directly from the Aries Cloud Agent - Python project
repository and made available through the [Github Packages Container
Registry](https://ghcr.io).


## Image

This project builds and publishes the `ghcr.io/hyperledger/aries-cloudagent-python` image.
Multiple variants are available; see [Tags](#tags).

### Tags

ACA-Py is a foundation for building decentralized identity applications; to this
end, there are multiple variants of ACA-Py built to suit the needs of a variety
of environments and workflows. There are currently two main variants:

- "Standard" - The default configuration of ACA-Py, including:
    - Aries Askar for secure storage
    - Indy VDR for Indy ledger communication
    - Indy Shared Libraries for AnonCreds
- "Indy" - The legacy configuration of ACA-Py, including:
    - Indy SDK Wallet for secure storage
    - Indy SDK Ledger for Indy ledger communication
    - Indy SDK for AnonCreds

These two image variants are largely distinguished by providers for Indy Network
and AnonCreds support. The Standard variant is recommended for new projects.
Migration from an Indy based image (whether the new Indy image variant or the
original BC Gov images) to the Standard image is outside of the scope of this
document.

The ACA-Py images built by this project are tagged to indicate which of the
above variants it is. Other tags may also be generated for use by developers.

Below is a table of all generated images and their tags:

Tag                     | Variant  | Example                  | Description                                                                                     |
------------------------|----------|--------------------------|-------------------------------------------------------------------------------------------------|
py3.6-X.Y.Z             | Standard | py3.6-0.7.4              | Standard image variant built on Python 3.6 for ACA-Py version X.Y.Z                             |
py3.7-X.Y.Z             | Standard | py3.7-0.7.4              | Standard image variant built on Python 3.7 for ACA-Py version X.Y.Z                             |
py3.8-X.Y.Z             | Standard | py3.8-0.7.4              | Standard image variant built on Python 3.8 for ACA-Py version X.Y.Z                             |
py3.9-X.Y.Z             | Standard | py3.9-0.7.4              | Standard image variant built on Python 3.9 for ACA-Py version X.Y.Z                             |
py3.10-X.Y.Z            | Standard | py3.10-0.7.4             | Standard image variant built on Python 3.10 for ACA-Py version X.Y.Z                            |
py3.7-indy-A.B.C-X.Y.Z  | Indy     | py3.7-indy-1.16.0-0.7.4  | Standard image variant built on Python 3.7 for ACA-Py version X.Y.Z and Indy SDK Version A.B.C  |
py3.8-indy-A.B.C-X.Y.Z  | Indy     | py3.8-indy-1.16.0-0.7.4  | Standard image variant built on Python 3.8 for ACA-Py version X.Y.Z and Indy SDK Version A.B.C  |
py3.9-indy-A.B.C-X.Y.Z  | Indy     | py3.9-indy-1.16.0-0.7.4  | Standard image variant built on Python 3.9 for ACA-Py version X.Y.Z and Indy SDK Version A.B.C  |
py3.10-indy-A.B.C-X.Y.Z | Indy     | py3.10-indy-1.16.0-0.7.4 | Standard image variant built on Python 3.10 for ACA-Py version X.Y.Z and Indy SDK Version A.B.C |

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
- Indy Image
    - Based on slim variant of Debian
    - Built from multi-stage build step (`indy-base` in the Dockerfile) which includes Indy dependencies; this could be replaced with an explicit `indy-python` image from the Indy SDK repo
    - Includes `libindy` but does **NOT** include the Indy CLI
    - Default user is `indy`
    - Uses container's system python environment rather than `pyenv`
    - Askar and Indy Shared libraries are installed as dependencies of ACA-Py through pip from pre-compiled binaries included in the python wrappers
    - Built from repo contents
    - Includes Indy postgres storage plugin
- `bcgovimages/aries-cloudagent`
    - (Usually) based on Ubuntu
    - Based on `von-image`
    - Default user is `indy`
    - Includes `libindy` and Indy CLI
    - Uses `pyenv`
    - Askar and Indy Shared libraries built from source
    - Built from ACA-Py python package uploaded to PyPI
    - Includes Indy postgres storage plugin

## Github Actions

- Tests (`.github/workflows/tests.yml`) - A reusable workflow that runs tests
  for the Standard ACA-Py variant for a given python version.
- Tests (Indy) (`.github/workflows/tests-indy.yml`) - A reusable workflow that
  runs tests for the Indy ACA-Py variant for a given python and indy version.
- PR Tests (`.github/workflows/pr-tests.yml`) - Run on pull requests; runs tests
  for the Standard and Indy ACA-Py variants for a "default" python version.
  Check this workflow for the current default python and Indy versions in use.
- Nightly Tests (`.github/workflows/nightly-tests.yml`) - Run nightly; runs
  tests for the Standard and Indy ACA-Py variants for all currently supported
  python versions. Check this workflow for the set of currently supported
  versions and Indy version(s) in use.
- Publish (`.github/workflows/publish.yml`) - Run on new release published or
  when manually triggered; builds and pushes the Standard ACA-Py variant to the
  Github Container Registry.
- Publish (Indy) (`.github/workflows/publish-indy.yml`) - Run on new release
  published or when manually triggered; builds and pushes the Indy ACA-Py
  variant to the Github Container Registry.
- Integration Tests (`.github/workflows/integrationtests.yml`) - Run on pull
  requests (to the hyperledger fork only); runs BDD integration tests.
- Black Format (`.github/workflows/blackformat.yml`) - Run on pull requests;
  checks formatting of files modified by the PR.
- CodeQL (`.github/workflows/codeql.yml`) - Run on pull requests; performs
  CodeQL analysis.
- Python Publish (`.github/workflows/pythonpublish.yml`) - Run on release
  created; publishes ACA-Py python package to PyPI.
- PIP Audit (`.github/workflows/pipaudit.yml`) - Run when manually triggered;
  performs pip audit.
