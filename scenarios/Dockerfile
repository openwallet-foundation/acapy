FROM python:3.13@sha256:34dc8eb488136014caf530ec03a3a2403473a92d67a01a26256c365b5b2fc0d4

WORKDIR /usr/src/app/

ENV POETRY_VERSION=2.1.1
ENV POETRY_HOME=/opt/poetry
RUN curl --proto "=https" --tlsv1.2 -sSf -L https://install.python-poetry.org | python -


ENV PATH="/opt/poetry/bin:$PATH"
RUN poetry config virtualenvs.in-project true

# Setup project
COPY pyproject.toml poetry.lock README.md ./
RUN poetry install

COPY examples/ examples/

ENTRYPOINT ["poetry", "run"]