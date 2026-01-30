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

# pybool_ir lucene results in assertion error -> force download of older lupyne version    
RUN --mount=type=cache,target=/opt/uv-cache \
    uv pip install --system --force-reinstall "lupyne<3.0.0"

# PyLucene
RUN --mount=type=cache,target=/opt/uv-cache \
    uv run -m pip install /pybool_ir/pylucene/dist/*.whl

# Installing pybool_ir from repo
RUN --mount=type=cache,target=/opt/uv-cache \
    uv run -m pip install --retries 5 --timeout 2000 -e /pybool_ir

# API dependencies
RUN uv pip install --system "fastapi[standard]"

# ---------- App ----------
COPY ./app /app
RUN chmod +x /app/entrypoint.sh

EXPOSE 8333
ENTRYPOINT ["/app/entrypoint.sh"]