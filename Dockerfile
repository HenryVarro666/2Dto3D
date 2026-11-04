# syntax=docker/dockerfile:1.7
# Model-free API + built web app by default (small, CPU only, no weights).
#
#   --build-arg WITH_MODELS=1   also installs the perception extras (Grounding DINO +
#                               SAM 2 via PyTorch) and the isolated VGGT worker
#                               environment under services/multiview/.venv, so the
#                               multi-view path runs inside the container. The image
#                               grows by several GB (PyPI CUDA wheels); run it with
#                               --gpus all for CUDA or PV3D_DEVICE=cpu otherwise.
#
# Model weights are never baked in: mount /app/models/huggingface and prepare them
# once with `python -m pv3d.perception` and `services/multiview/infer.py --prepare`.

FROM node:22-bookworm-slim AS web
WORKDIR /src/apps/web
COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci --no-audit --no-fund
# The replay panels import frozen measurement records from the repository's docs tree.
COPY docs/measurement /src/docs/measurement
COPY apps/web ./
RUN npm run build

FROM python:3.12-slim-bookworm AS runtime
ARG WITH_MODELS=0
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_FROZEN=1
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /usr/local/bin/uv
# git is needed only to resolve the pinned VGGT git dependency of the worker environment.
RUN if [ "$WITH_MODELS" = "1" ]; then \
        apt-get update && apt-get install -y --no-install-recommends git \
        && rm -rf /var/lib/apt/lists/*; \
    fi
WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
# Dependencies first so source edits do not invalidate the dependency layer.
RUN --mount=type=cache,target=/root/.cache/uv \
    if [ "$WITH_MODELS" = "1" ]; then uv sync --no-dev --no-install-project --extra ml; \
    else uv sync --no-dev --no-install-project; fi
COPY services/api ./services/api
COPY services/multiview/infer.py services/multiview/pyproject.toml services/multiview/uv.lock ./services/multiview/
COPY scripts ./scripts
RUN --mount=type=cache,target=/root/.cache/uv \
    if [ "$WITH_MODELS" = "1" ]; then \
        uv sync --no-dev --extra ml \
        && uv sync --project services/multiview; \
    else uv sync --no-dev; fi
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
