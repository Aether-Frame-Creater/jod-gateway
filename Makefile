.PHONY: setup dev test lint fmt

setup:
	uv sync --extra dev

dev:
	uv run uvicorn jod_gateway.main:app --reload --port 8080

test:
	uv run --extra dev pytest -v

lint:
	uv run --extra dev ruff check src tests

fmt:
	uv run --extra dev ruff format src tests