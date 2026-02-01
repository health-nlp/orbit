FROM ghcr.io/hscells/pybool_ir:master

ENV UV_CACHE_DIR=/opt/uv-cache \
    UV_PYTHON_CACHE_DIR=/opt/uv-cache/python \
    UV_LINK_MODE=copy

WORKDIR /app

# ---------- Dependencies ----------
RUN pip install --retries=10 --default-timeout=500 uv

COPY pyproject.toml uv.lock ./
# Base dependencies
RUN --mount=type=cache,target=/opt/uv-cache \
    uv sync

# PyLucene
RUN --mount=type=cache,target=/opt/uv-cache \
    uv run -m pip install /pybool_ir/pylucene/dist/*.whl

ENV JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64
ENV JCC_JDK=${JAVA_HOME}

# Installing pybool_ir from repo
RUN --mount=type=cache,target=/opt/uv-cache \
    uv run -m pip install /pybool_ir

# API dependencies
RUN uv pip install --system "fastapi[standard]"

RUN uv add "jcc"

# ---------- App ----------
COPY ./app /app
RUN chmod +x /app/entrypoint.sh

EXPOSE 8333
ENTRYPOINT ["/app/entrypoint.sh"]
