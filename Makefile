.PHONY: verify fix lint format format-check type-check install test test-cov test-integration test-uk-data-client test-uk-data-client-integration test-matrix test-matrix-cov pysentry docs docs-serve build-rust benchmark

# Verify - check everything without making changes
verify: lint format-check type-check

# Fix - automatically fix what can be fixed
fix:
	uv run ruff check --fix .
	uv run ruff format .

# Individual targets
lint:
	uv run ruff check .

format-check:
	uv run ruff format --check .

format:
	uv run ruff format .

type-check:
	uv run ty check

# Install all dependencies
install:
	uv sync --all-groups

# Run tests (all packages, excluding integration)
test:
	uv run pytest tests/ packages/uk-data-client/tests/ -m "not integration" -v

# Run tests with coverage
test-cov:
	uv run pytest -m "not integration" --cov --cov-report=xml --cov-report=term-missing

# Run live-source integration tests explicitly
test-integration:
	uv run pytest tests/ packages/uk-data-client/tests/ -m integration -v

# Run uk-data-client unit tests only
test-uk-data-client:
	uv run pytest packages/uk-data-client/tests/ -m "not integration" -v

# Run uk-data-client integration tests only
test-uk-data-client-integration:
	uv run pytest packages/uk-data-client/tests/ -m integration -v

# Run tests across all Python versions
test-matrix:
	uv run hatch test

# Run tests with coverage across all Python versions
test-matrix-cov:
	uv run hatch test --cover


# Dependency vulnerability scanning
pysentry:
	uv run pysentry-rs


# Build the Rust ABM extension (requires cargo + maturin)
build-rust:
	./scripts/build_rust_abm.sh

# Run ABM performance benchmark (Python vs Rust)
benchmark:
	uv run python scripts/run_benchmark.py

# Documentation
docs:
	uv run mkdocs build

docs-serve:
	uv run mkdocs serve
