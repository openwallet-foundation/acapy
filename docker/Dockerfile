ARG python_version=3.9.16
FROM python:${python_version}-slim-bullseye AS build

WORKDIR /src

ADD . .

RUN pip install setuptools wheel
RUN python setup.py sdist bdist_wheel

FROM python:${python_version}-slim-bullseye AS main

ARG uid=1001
ARG user=aries
ARG acapy_version
ARG acapy_reqs=[askar,bbs]

ENV HOME="/home/$user" \
    APP_ROOT="$HOME" \
    LC_ALL=C.UTF-8 \
    LANG=C.UTF-8 \
    PIP_NO_CACHE_DIR=off \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=UTF-8 \
    RUST_LOG=warning \
    SHELL=/bin/bash \
    SUMMARY="aries-cloudagent image" \
    DESCRIPTION="aries-cloudagent provides a base image for running Hyperledger Aries agents in Docker. \
    This image layers the python implementation of aries-cloudagent $acapy_version. Based on Debian Buster."

LABEL summary="$SUMMARY" \
    description="$DESCRIPTION" \
    io.k8s.description="$DESCRIPTION" \
    io.k8s.display-name="aries-cloudagent $acapy_version" \
    name="aries-cloudagent" \
    acapy.version="$acapy_version" \
    maintainer=""

# Add aries user
RUN useradd -U -ms /bin/bash -u $uid $user

# Install environment
RUN apt-get update -y && \
    apt-get install -y --no-install-recommends \
    apt-transport-https \
    ca-certificates \
    build-essential \
    bzip2 \
    curl \
    git \
    less \
    libffi-dev \
    libgmp10 \
    liblzma5 \
    libncurses5 \
    libncursesw5 \
    libsecp256k1-0 \
    libzmq5 \
    net-tools \
    openssl \
    sqlite3 \
    vim-tiny \
    zlib1g && \
    rm -rf /var/lib/apt/lists/* /usr/share/doc/*

WORKDIR $HOME

# Add local binaries and aliases to path
ENV PATH="$HOME/.local/bin:$PATH"

# - In order to drop the root user, we have to make some directories writable
#   to the root group as OpenShift default security model is to run the container
#   under random UID.
RUN usermod -a -G 0 $user

# Create standard directories to allow volume mounting and set permissions
# Note: PIP_NO_CACHE_DIR environment variable should be cleared to allow caching
RUN mkdir -p \
    $HOME/.aries_cloudagent \
    $HOME/.cache/pip/http \
    $HOME/ledger/sandbox/data \
    $HOME/log

# The root group needs access the directories under $HOME/.aries_cloudagent for the container to function in OpenShift.
RUN chown -R $user:root $HOME/.aries_cloudagent && \
    chmod -R ug+rw $HOME/log $HOME/ledger $HOME/.aries_cloudagent $HOME/.cache

# Install ACA-py from the wheel as $user,
# and ensure the permissions on the python 'site-packages' and $HOME/.local folders are set correctly.
USER $user
COPY --from=build /src/dist/aries_cloudagent*.whl .
RUN aries_cloudagent_package=$(find ./ -name "aries_cloudagent*.whl" | head -n 1) && \
    echo "Installing ${aries_cloudagent_package} ..." && \
    pip install --no-cache-dir --find-links=. ${aries_cloudagent_package}${acapy_reqs} && \
    rm aries_cloudagent*.whl && \
    chmod +rx $(python -m site --user-site) $HOME/.local

# Clean-up unneccessary build dependencies and reduce final image size
USER root
RUN apt-get purge -y --auto-remove build-essential

USER $user

ENTRYPOINT ["aca-py"]
