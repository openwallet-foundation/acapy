FROM python:3.10@sha256:7118d485696a1eb1105ae30e3f55e5685117a9bc0c3ffbe3830a268911e0837d

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