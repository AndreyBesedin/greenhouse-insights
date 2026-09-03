.PHONY: help backend-install backend-dev backend-test backend-lint backend-typecheck backend-eval \
	frontend-install frontend-dev frontend-test frontend-lint frontend-build \
	test lint docker-build docker-up docker-down docker-logs

help:
	@echo "backend-install   install backend dependencies with Poetry"
	@echo "backend-dev       run the backend dev server (uvicorn --reload)"
	@echo "backend-test      run backend tests"
	@echo "backend-lint      run ruff + mypy on the backend"
	@echo "backend-eval      run the agent decision-quality evaluation scorecard"
	@echo "frontend-install  install frontend dependencies"
	@echo "frontend-dev      run the frontend dev server (vite)"
	@echo "frontend-test     run frontend tests"
	@echo "frontend-lint     run eslint + prettier --check on the frontend"
	@echo "frontend-build    build the frontend for production"
	@echo "test              run backend and frontend tests"
	@echo "lint              run all lint/type checks (backend and frontend)"
	@echo "docker-build      build the backend and frontend Docker images"
	@echo "docker-up         start the app with docker compose (detached)"
	@echo "docker-down       stop the docker compose app"
	@echo "docker-logs       follow logs from the docker compose app"

backend-install:
	cd backend && poetry install

backend-dev:
	cd backend && poetry run uvicorn application.api.main:app --reload

backend-test:
	cd backend && poetry run pytest

backend-lint:
	cd backend && poetry run ruff check . && poetry run ruff format --check . && poetry run mypy .

backend-eval:
	cd backend && poetry run python -m management.evaluation

frontend-install:
	cd frontend && npm install --legacy-peer-deps

frontend-dev:
	cd frontend && npm run dev

frontend-test:
	cd frontend && npm test

frontend-lint:
	cd frontend && npm run lint && npm run format:check

frontend-build:
	cd frontend && npm run build

test: backend-test frontend-test

lint: backend-lint frontend-lint

docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f
