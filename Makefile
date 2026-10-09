.PHONY: all help install dev lint format typecheck test test-cov build gen-api check clean docker-up docker-down

help:
	@echo "Nuvorix Engineering Commands:"
	@echo "  make install     - Install all backend (uv) and frontend (npm) dependencies"
	@echo "  make lint        - Run Ruff linting and frontend ESLint"
	@echo "  make format      - Run Ruff code formatting"
	@echo "  make typecheck   - Run Mypy (backend) and TypeScript compiler (frontend)"
	@echo "  make test        - Run backend pytest and frontend Vitest"
	@echo "  make test-cov    - Run pytest with code coverage report"
	@echo "  make build       - Build frontend bundle and verify backend packaging"
	@echo "  make gen-api     - Export backend OpenAPI schema to docs/openapi.json"
	@echo "  make check       - Execute full quality gate (lint, format check, typecheck, test, build)"
	@echo "  make docker-up   - Start full platform stack via docker compose"
	@echo "  make docker-down - Stop docker compose services"

install:
	uv sync --extra dev
	cd frontend && npm install

lint:
	uv run ruff check backend packages
	cd frontend && npm run lint

format:
	uv run ruff format backend packages

typecheck:
	uv run mypy backend/app packages/cli packages/sdk-python
	cd frontend && npm run typecheck

test:
	uv run pytest -v
	cd frontend && npm test

test-cov:
	uv run pytest --cov=backend.app --cov-report=term-missing --cov-report=html:coverage_html -v

build:
	cd frontend && npm run build

gen-api:
	uv run python scripts/gen_openapi_schema.py

check: lint typecheck test-cov build
	@echo "=== Nuvorix Quality Gate Passed Successfully ==="

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down

clean:
	rm -rf .pytest_cache .ruff_cache htmlcov coverage_html frontend/dist frontend/node_modules/.vite
