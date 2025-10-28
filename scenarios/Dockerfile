FROM python:3.10

WORKDIR /usr/src/app/

# Install uv
RUN pip install --no-cache-dir uv

# Setup project
COPY pyproject.toml README.md ./
RUN uv sync

COPY examples/ examples/

ENTRYPOINT ["uv", "run"]