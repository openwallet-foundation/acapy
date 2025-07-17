ARG python_version=3.12
FROM python:${python_version}-slim-bookworm AS build

RUN pip install --no-cache-dir poetry==2.1.1

WORKDIR /src

COPY ./pyproject.toml ./poetry.lock ./
RUN poetry install --no-root

COPY ./acapy_agent ./acapy_agent
COPY ./README.md /src
RUN poetry build

FROM python:${python_version}-slim-bookworm AS main

ARG uid=1001
ARG user=aries
ARG acapy_name="acapy-agent"
ARG acapy_version
ARG acapy_reqs=[didcommv2]

ENV HOME="/home/$user" \
    APP_ROOT="/home/$user" \
    LC_ALL=C.UTF-8 \
    LANG=C.UTF-8 \
    PIP_NO_CACHE_DIR=off \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=UTF-8 \
    RUST_LOG=warn \
    SHELL=/bin/bash \
    SUMMARY="$acapy_name image" \
    DESCRIPTION="$acapy_name provides a base image for running acapy agents in Docker. \
    This image layers the python implementation of $acapy_name $acapy_version. Based on Debian Buster."

LABEL summary="$SUMMARY" \
    description="$DESCRIPTION" \
    io.k8s.description="$DESCRIPTION" \
    io.k8s.display-name="$acapy_name $acapy_version" \
    name=$acapy_name \
    acapy.version="$acapy_version" \
    maintainer=""

# Add aries user
RUN useradd -U -ms /bin/bash -u $uid $user

# Install environment
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    apt-transport-https \
    ca-certificates \
    curl \
    git \
    libffi-dev \
    libgmp10 \
    libncurses5 \
    libncursesw5 \
    openssl \
    sqlite3 \
    zlib1g && \
    apt-get autopurge -y && \
    apt-get clean -y && \
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
    $HOME/.acapy_agent \
    $HOME/.cache/pip/http \
    $HOME/.indy_client \
    $HOME/ledger/sandbox/data \
    $HOME/log

# The root group needs access the directories under $HOME/.indy_client and $HOME/.acapy_agent for the container to function in OpenShift.
RUN chown -R $user:root $HOME/.indy_client $HOME/.acapy_agent && \
    chmod -R ug+rw $HOME/log $HOME/ledger $HOME/.acapy_agent $HOME/.cache $HOME/.indy_client

# Create /home/indy and symlink .indy_client folder for backwards compatibility with artifacts created on older indy-based images.
RUN mkdir -p /home/indy
RUN ln -s /home/aries/.indy_client /home/indy/.indy_client

# Install ACA-py from the wheel as $user,
# and ensure the permissions on the python 'site-packages' and $HOME/.local folders are set correctly.
USER $user
COPY --from=build /src/dist/acapy_agent*.whl .
RUN acapy_agent_package=$(find ./ -name "acapy_agent*.whl" | head -n 1) && \
    echo "Installing ${acapy_agent_package} ..." && \
    pip install --no-cache-dir --find-links=. ${acapy_agent_package}${acapy_reqs} && \
    rm acapy_agent*.whl && \
    chmod +rx $(python -m site --user-site) $HOME/.local

ENTRYPOINT ["aca-py"]
