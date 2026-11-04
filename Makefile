.PHONY: setup dev test build serve models setup-multiview models-multiview lint typecheck format check clean

PY := .venv/bin/python

setup:
	uv sync --frozen --extra dev --extra ml
	npm --prefix apps/web ci

dev:
	$(PY) scripts/dev.py

models:
	$(PY) -m pv3d.perception

setup-multiview:
	uv sync --project services/multiview --frozen

models-multiview:
	services/multiview/.venv/bin/python services/multiview/infer.py --prepare

test:
	$(PY) -m pytest
	npm --prefix apps/web test

lint:
	$(PY) -m ruff check services/api scripts services/multiview/infer.py
	npm --prefix apps/web run lint

typecheck:
	$(PY) -m mypy
	npm --prefix apps/web run typecheck

format:
	npm --prefix apps/web run format

check: lint typecheck test build

build:
	npm --prefix apps/web run build

serve:
	$(PY) -m pv3d

clean:
	rm -rf apps/web/dist .pytest_cache .mypy_cache .ruff_cache
