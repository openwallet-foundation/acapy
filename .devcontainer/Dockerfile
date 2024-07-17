# See here for image contents: https://github.com/microsoft/vscode-dev-containers/tree/v0.134.0/containers/python-3/.devcontainer/base.Dockerfile
ARG VARIANT="3.12"
FROM mcr.microsoft.com/devcontainers/python:${VARIANT}

ARG POETRY_VERSION="1.4"
ENV POETRY_HOME="/opt/poetry" \
    POETRY_VERSION=${POETRY_VERSION}

RUN curl -sSL https://install.python-poetry.org | python3 - \
    && update-alternatives --install /usr/local/bin/poetry poetry /opt/poetry/bin/poetry 900 \
    # Enable tab completion for bash
    && poetry completions bash >> /home/vscode/.bash_completion \
    # Enable tab completion for Zsh
    && mkdir -p /home/vscode/.zfunc/ \
    && poetry completions zsh > /home/vscode/.zfunc/_poetry \
    && echo "fpath+=~/.zfunc\nautoload -Uz compinit && compinit" >> /home/vscode/.zshrc

COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false \
    && poetry install --no-root --no-interaction --all-extras \
    && rm -rf /root/.cache/pypoetry
