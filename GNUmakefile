# GNUmakefile for easy development workflows.
# See doc/development.md for docs.
# Note GitHub Actions call uv directly, not this GNUmakefile.

.DEFAULT_GOAL := default

.PHONY: default venv install lint test upgrade build clean

default: venv install lint test

venv:
	# For development purposes, use 3.13 to ensure backward-compatibility
	uv venv --python 3.13

install:
	@test -d .venv || $(MAKE) venv
	uv sync --all-extras

lint:
	uv run python devtools/lint.py

test:
	uv run pytest

upgrade:
	uv sync --upgrade --all-extras --dev

build:
	uv build

clean:
	-rm -rf dist/
	-rm -rf .venv/
	-find . -type d -name "__pycache__" -exec rm -rf {} +
