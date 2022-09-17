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


## Images

The following images are built from this project

- `ghcr.io/hyperledger/aries-cloudagent-python` - multiple variants are built
  from this project; see [Tags](#tags).
- `ghcr.io/hyperledger/indy-python` - this image is used as a base for the
  ACA-Py Indy variant (see [Tags](#tags)). This may be moved to a more
  appropriate project in the future.


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
above variants it is. Other tags are also generated for use by developers.

Below is a table of all generated images and their tags:

Tag                     | Variant  | Example                  | Description                                                                                     |
------------------------|----------|--------------------------|-------------------------------------------------------------------------------------------------|
py3.7-X.Y.Z             | Standard | py3.7-0.7.4              | Standard image variant built on Python 3.7 for ACA-Py version X.Y.Z                             |
py3.8-X.Y.Z             | Standard | py3.8-0.7.4              | Standard image variant built on Python 3.8 for ACA-Py version X.Y.Z                             |
py3.9-X.Y.Z             | Standard | py3.9-0.7.4              | Standard image variant built on Python 3.9 for ACA-Py version X.Y.Z                             |
py3.10-X.Y.Z            | Standard | py3.10-0.7.4             | Standard image variant built on Python 3.10 for ACA-Py version X.Y.Z                            |
py3.7-indy-A.B.C-X.Y.Z  | Indy     | py3.7-indy-1.16.0-0.7.4  | Standard image variant built on Python 3.7 for ACA-Py version X.Y.Z and Indy SDK Version A.B.C  |
py3.8-indy-A.B.C-X.Y.Z  | Indy     | py3.8-indy-1.16.0-0.7.4  | Standard image variant built on Python 3.8 for ACA-Py version X.Y.Z and Indy SDK Version A.B.C  |
py3.9-indy-A.B.C-X.Y.Z  | Indy     | py3.9-indy-1.16.0-0.7.4  | Standard image variant built on Python 3.9 for ACA-Py version X.Y.Z and Indy SDK Version A.B.C  |
py3.10-indy-A.B.C-X.Y.Z | Indy     | py3.10-indy-1.16.0-0.7.4 | Standard image variant built on Python 3.10 for ACA-Py version X.Y.Z and Indy SDK Version A.B.C |


#### Indy Python

**Image Name:** `ghcr.io/hyperledger/indy-python`

The Indy Python image is used as a base for the Indy variant of ACA-Py. It is a
debian based image with `libindy` and the Indy SDK Python wrapper installed.

Below is a table of all generated Indy Python images and their tags:

Tag                     | Example                  | Description                             |
------------------------|--------------------------|-----------------------------------------|
py3.7-X.Y.Z             | py3.7-1.16.0             | Python 3.7 with Indy SDK version X.Y.Z  |
py3.8-X.Y.Z             | py3.8-1.16.0             | Python 3.8 with Indy SDK version X.Y.Z  |
py3.9-X.Y.Z             | py3.9-1.16.0             | Python 3.9 with Indy SDK version X.Y.Z  |
py3.10-X.Y.Z            | py3.10-1.16.0            | Python 3.10 with Indy SDK version X.Y.Z |


#### Nightly

The Github Actions will also produce Nightly builds of ACA-Py. If a nightly
build at the current hash of the repo doesn't yet exist, GHA will build a
standard and Indy ACA-Py image at midnight each day. Nightly builds are produced
only for the current "active" python version.

Below is a table of all generated Nightly images and their tags:

Tag                                        | Variant  | Example                                                            | Description                           |
-------------------------------------------|----------|--------------------------------------------------------------------|---------------------------------------|
py3.7-nightly                              | Standard | py3.7-nightly                                                      | Standard image latest nightly         |
py3.7-indy-A.B.C-nightly                   | Indy     | py3.7-indy-1.16.0-nightly                                          | Indy image latest nightly             |
py3.7-nightly-{{ commit hash }}            | Standard | py3.7-nightly-96bc6a8938f0c0e2a487a069d63bcb6c8172b320             | Standard image nightly at commit hash |
py3.7-indy-A.B.C-nightly-{{ commit hash }} | Indy     | py3.7-indy-1.16.0-nightly-96bc6a8938f0c0e2a487a069d63bcb6c8172b320 | Indy image nightly at commit hash     |


#### Testing

The Github Actions will produce images used in CI/CD checks for Indy (Indy image
tests require `libindy` which is not available on Github runners; these tests
must be run inside of a container with `libindy`). These images are only
intended for use by these checks.

Below is a table of all generated test images and their tags:

Image + Tag                                                                                             | Description                        |
--------------------------------------------------------------------------------------------------------|------------------------------------|
indy-python-test:py{{python-version}}-{{indy-version}}-{{hash of indy base Dockerfile}}                 | Base Indy Python image for testing |
acapy-test:py{{python-version}}-{{indy-version}}-{{hash of requirements*.txt and indy test Dockerfile}} | ACA-Py test image                  |

## Github Actions

Several Github Actions are used to produce the above described images.

**TODO:** Add descriptions of actions

## Key Differences

There are several key differences that should be noted between the two image
variants and between the BC Gov ACA-Py images and VON images and the images
produced by this project.

- Standard Image
    - Based on slim variant of Debian
    - Does **NOT** include `libindy`
    - Default user is `aries`
    - Uses container's system python environment rather than `pyenv`
    - Askar and Indy Shared libraries are installed through pip from
      pre-compiled binaries included in the python wrappers.
    - Built from repo contents
- Indy Image
    - Based on slim variant of Debian
    - Based on `indy-python`
    - Includes `libindy` but does **NOT** include the Indy CLI
    - Default user is `indy`
    - Based on `indy-python`
    - Uses container's system python environment rather than `pyenv`
    - Askar and Indy Shared libraries are installed through pip from
      pre-compiled binaries included in the python wrappers
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
