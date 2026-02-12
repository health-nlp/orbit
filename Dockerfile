FROM ghcr.io/hscells/pybool_ir:master

ENV UV_CACHE_DIR=/opt/uv-cache \
    UV_PYTHON_CACHE_DIR=/opt/uv-cache/python \
    UV_LINK_MODE=copy

WORKDIR /app

# ---------- Dependencies ----------
RUN pip install --retries=10 --default-timeout=500 uv
RUN python3 -m ensurepip
RUN uv run python -m ensurepip

COPY pyproject.toml ./
# Base dependencies
RUN --mount=type=cache,target=/opt/uv-cache \
    uv sync

# PyLucene
RUN --mount=type=cache,target=/opt/uv-cache \
    uv run -m pip install /pybool_ir/pylucene/dist/*.whl

# Installing pybool_ir from repo
ENV JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64
ARG JCC_JDK=${JAVA_HOME}
ARG JCC_ARGSEP=";"
ARG JCC_LFLAGS="-L$JAVA_HOME/lib;-ljava;-L$JAVA_HOME/lib/server;-ljvm;-Wl,-rpath=$JAVA_HOME/lib:$JAVA_HOME/lib/server"
ARG JCC="python -m jcc --wheel"
RUN uv add /pybool_ir/pylucene/jcc

RUN --mount=type=cache,target=/opt/uv-cache uv run -m pip install /pybool_ir

# API dependencies
RUN uv add "fastapi[standard]"

# ---------- App ----------
COPY ./app /app
RUN chmod +x /app/entrypoint.sh

EXPOSE 8333
ENTRYPOINT ["/app/entrypoint.sh"]
