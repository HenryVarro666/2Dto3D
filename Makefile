.PHONY: setup dev test build serve models

setup:
	uv sync --frozen --extra dev --extra ml
	npm --prefix apps/web ci

dev:
	.venv/bin/python scripts/dev.py

models:
	.venv/bin/python -m pv3d.perception

test:
	.venv/bin/python -m pytest
	npm --prefix apps/web test

build:
	npm --prefix apps/web run build

serve:
	.venv/bin/python -m uvicorn pv3d.app:create_app --factory --host 127.0.0.1 --port 8000
