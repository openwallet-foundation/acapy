ARG python_version=3.12
FROM python:${python_version}-slim-bookworm AS build

# Install Poetry
RUN pip install --no-cache-dir poetry==2.1.1

# Install build dependencies for compiling extensions like pysqlcipher3 to Support DB Manager
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    g++ \
    gcc \
    libsqlcipher-dev \
    libsqlite3-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /src

COPY ./pyproject.toml ./poetry.lock ./
# need to install pysqlcipher3 first to ensure build dependencies are available
RUN pip install --no-cache-dir pysqlcipher3==1.2.0 && \
    poetry install --no-root

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

# Install runtime environment
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    apt-transport-https \
    build-essential \
    ca-certificates \
    curl \
    git \
    libffi-dev \
    libgmp10 \
    libncurses5 \
    libncursesw5 \
    libpq-dev \
    libsqlcipher-dev \
    openssl \
    postgresql-client \
    sqlite3 \
    zlib1g && \
    apt-get autoremove --purge -y && \
    apt-get clean -y && \
    rm -rf /var/lib/apt/lists/* /usr/share/doc/*

WORKDIR $HOME

# Add local binaries and aliases to path
ENV PATH="$HOME/.local/bin:$PATH"

# In order to drop the root user, make directories writable for OpenShift
RUN usermod -a -G 0 $user

# Create standard directories for volume mounting and set permissions
RUN mkdir -p \
    $HOME/.acapy_agent \
    $HOME/.cache/pip/http \
    $HOME/.indy_client \
    $HOME/ledger/sandbox/data \
    $HOME/log

# Set permissions for OpenShift compatibility
RUN chown -R $user:root $HOME/.indy_client $HOME/.acapy_agent && \
    chmod -R ug+rw $HOME/log $HOME/ledger $HOME/.acapy_agent $HOME/.cache $HOME/.indy_client

# Create /home/indy and symlink .indy_client for backwards compatibility
RUN mkdir -p /home/indy
RUN ln -s /home/aries/.indy_client /home/indy/.indy_client

# Install ACA-Py from the wheel as $user
USER $user
COPY --from=build /src/dist/acapy_agent*.whl .
RUN acapy_agent_package=$(find ./ -name "acapy_agent*.whl" | head -n 1) && \
    echo "Installing ${acapy_agent_package} ..." && \
    pip install --no-cache-dir --find-links=. ${acapy_agent_package}${acapy_reqs} && \
    rm acapy_agent*.whl && \
    chmod +rx $(python -m site --user-site) $HOME/.local

ENTRYPOINT ["aca-py"]