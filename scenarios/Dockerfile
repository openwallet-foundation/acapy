FROM python:3.10

WORKDIR /usr/src/app/

ENV POETRY_VERSION=1.8.3
ENV POETRY_HOME=/opt/poetry
RUN curl --proto "=https" --tlsv1.2 -sSf -L https://install.python-poetry.org | python -


ENV PATH="/opt/poetry/bin:$PATH"
RUN poetry config virtualenvs.in-project true

# Setup project
COPY pyproject.toml poetry.lock README.md ./
RUN poetry install

COPY examples/ examples/

ENTRYPOINT ["poetry", "run"]