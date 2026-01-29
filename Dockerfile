FROM ghcr.io/hscells/pybool_ir:master

ENV UV_CACHE_DIR=/opt/uv-cache \
    UV_PYTHON_CACHE_DIR=/opt/uv-cache/python \
    UV_LINK_MODE=copy

WORKDIR /app

# ---------- Dependencies ----------
RUN pip install --retries=10 --default-timeout=500 uv

COPY pyproject.toml uv.lock /app/

# Base dependencies
RUN --mount=type=cache,target=/opt/uv-cache \
    uv sync

# PyLucene + pybool_ir
RUN --mount=type=cache,target=/opt/uv-cache \
    uv run -m pip install /pybool_ir/pylucene/dist/*.whl

RUN --mount=type=cache,target=/opt/uv-cache \
    uv run -m pip install --retries 5 --timeout 2000 -e /pybool_ir

# API dependencies
#RUN uv add fastapi --extra standard
#RUN uv run -m pip install "fastapi[standard]"
RUN uv pip install --system "fastapi[standard]"

# ---------- App ----------
COPY main.py /app/
COPY pybool_ir /app/pybool_ir
COPY searchresult.py /app/searchresult.py
# COPY index-pubmed.sh /index-pubmed.sh
COPY entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
