# syntax=docker/dockerfile:1.7
# Model-free API + built web app. Pass --build-arg UV_EXTRAS=ml to include the
# perception stack (large; CUDA wheels on Linux). The VGGT worker environment is
# a separate, isolated install (services/multiview) and is not part of this image.

FROM node:22-bookworm-slim AS web
WORKDIR /src/apps/web
COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY apps/web ./
RUN npm run build

FROM python:3.12-slim-bookworm AS runtime
ARG UV_EXTRAS=""
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_FROZEN=1
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
# Dependencies first so source edits do not invalidate the dependency layer.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev --no-install-project ${UV_EXTRAS:+--extra "$UV_EXTRAS"}
COPY services/api ./services/api
COPY services/multiview/infer.py services/multiview/pyproject.toml ./services/multiview/
COPY scripts ./scripts
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev ${UV_EXTRAS:+--extra "$UV_EXTRAS"}
COPY --from=web /src/apps/web/dist ./apps/web/dist
RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin pv3d \
    && mkdir -p /app/data/runtime /app/models/huggingface \
    && chown -R pv3d:pv3d /app/data /app/models
USER pv3d
ENV PV3D_HOST=0.0.0.0 \
    PV3D_PORT=8000 \
    PV3D_DATA_DIR=/app/data/runtime \
    PV3D_MODEL_DIR=/app/models/huggingface \
    PV3D_LOG_FORMAT=json
VOLUME ["/app/data/runtime", "/app/models/huggingface"]
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["/app/.venv/bin/python", "-c", "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4).status == 200 else 1)"]
CMD ["/app/.venv/bin/python", "-m", "pv3d"]
