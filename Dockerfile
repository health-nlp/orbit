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

# Installing pybool_ir from repo
RUN --mount=type=cache,target=/opt/uv-cache \
    uv run -m pip install --retries 5 --timeout 2000 -e /pybool_ir

# API dependencies
RUN uv pip install --system "fastapi[standard]"

# ---------- App ----------
COPY ./app ./


# outcommented - will be deleted if not needed anymore
#COPY searchresult.py /app/searchresult.py
#COPY main.py /app/main.py
COPY entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

EXPOSE 8333

ENTRYPOINT ["/entrypoint.sh"]