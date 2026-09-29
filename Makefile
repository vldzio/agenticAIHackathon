PY ?= python
.PHONY: help install dev-api dev-web test test-api test-web lint format typecheck train openapi build docker-up check

help:            ## list targets
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-12s %s\n", $$1, $$2}'

install:         ## install backend + frontend dependencies
	cd backend && $(PY) -m pip install -r requirements-dev.txt
	cd frontend && npm ci

dev-api:         ## run the API with auto-reload on :8000
	cd backend && $(PY) -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-web:         ## run the frontend dev server on :5173 (proxies /api to :8000)
	cd frontend && npm run dev

test: test-api test-web  ## run all tests

test-api:
	cd backend && $(PY) -m pytest tests --cov=app --cov-report=term-missing:skip-covered

test-web:
	cd frontend && npm test

lint:            ## ruff + formatting check + TypeScript typecheck
	cd backend && $(PY) -m ruff check . && $(PY) -m ruff format --check .
	cd frontend && npm run typecheck

format:
	cd backend && $(PY) -m ruff check --fix . && $(PY) -m ruff format .

typecheck:       ## mypy
	cd backend && $(PY) -m mypy app ml_pipeline scripts

train:           ## clean data, retrain both models, evaluate, write backend/artifacts/*
	cd backend && $(PY) -m ml_pipeline.train

openapi:         ## regenerate frontend/openapi.json and the TypeScript API types
	cd backend && AETHERFIT_DATABASE_URL=sqlite:///:memory: $(PY) -m scripts.export_openapi ../frontend/openapi.json
	cd frontend && npm run gen:api

build:           ## production frontend bundle
	cd frontend && npm run build

docker-up:       ## build and start the full stack on http://localhost:8080
	docker compose up --build

check: lint typecheck test  ## everything CI runs
