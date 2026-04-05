# GNUmakefile for easy development workflows.
# See doc/development.md for docs.
# Note GitHub Actions call uv directly, not this GNUmakefile.

.DEFAULT_GOAL := install

# Colors
CYAN    = \033[36m
GREEN   = \033[32m
RED     = \033[31m
NC      = \033[0m

venv:
	uv venv

install:
	@test -d .venv || $(MAKE) venv
	uv sync --all-extras

dev: install-dev
install-dev:
	@test -d .venv || $(MAKE) venv
	uv sync --all-extras --dev

lint: lint-codespell lint-ruff-check lint-ruff-format lint-basedpyright lint-git-diff

lint-codespell:
	@printf "$(CYAN)Codespell check...$(NC)\\n"; (set -x ; uv run codespell .); \
	if [ $$? -eq 0 ]; then printf "$(GREEN)✅ Codespell check passed!$(NC)\\n\\n"; \
	else printf "$(RED)❌ Codespell check failed!$(NC)\\n\\n"; exit 1; \
	fi

lint-ruff-check:
	@printf "$(CYAN)Ruff check...$(NC)\\n"; (set -x ; uv run ruff check .); \
	if [ $$? -eq 0 ]; then printf "$(GREEN)✅ Ruff check passed!$(NC)\\n\\n"; \
	else printf "$(RED)❌ Ruff check failed!$(NC)\\n\\n"; exit 1; \
	fi

lint-ruff-format:
	@printf "$(CYAN)Ruff format check...$(NC)\\n"; (set -x ; uv run ruff format --check .); \
	if [ $$? -eq 0 ]; then printf "$(GREEN)✅ Ruff format check passed!$(NC)\\n\\n"; \
	else printf "$(RED)❌ Ruff format check failed!$(NC)\\n\\n"; exit 1; \
	fi

lint-basedpyright:
	@printf "$(CYAN)Basedpyright check...$(NC)\\n"; (set -x ; uv run basedpyright); \
	if [ $$? -eq 0 ]; then printf "$(GREEN)✅ Basedpyright check passed!$(NC)\\n\\n"; \
	else printf "$(RED)❌ Basedpyright check failed!$(NC)\\n\\n"; exit 1; \
	fi

lint-git-diff:
	@printf "$(CYAN)Git diff check...$(NC)\\n"; (set -x ; git diff --check HEAD); \
	if [ $$? -eq 0 ]; then printf "$(GREEN)✅ Git diff check passed!$(NC)\\n\\n"; \
	else printf "$(RED)❌ Git diff check failed!$(NC)\\n\\n"; exit 1; \
	fi

fix: fix-codespell fix-ruff-check fix-ruff-format

fix-codespell:
	@printf "$(CYAN)Codespell fix...$(NC)\\n"; (set -x ; uv run codespell --write-changes .); \
	if [ $$? -eq 0 ]; then printf "$(GREEN)✅ Codespell fix passed!$(NC)\\n\\n"; \
	else printf "$(RED)❌ Codespell fix failed!$(NC)\\n\\n"; exit 1; \
	fi

fix-ruff-check:
	@printf "$(CYAN)Ruff fix...$(NC)\\n"; (set -x ; uv run ruff check --fix .); \
	if [ $$? -eq 0 ]; then printf "$(GREEN)✅ Ruff fix passed!$(NC)\\n\\n"; \
	else printf "$(RED)❌ Ruff fix failed!$(NC)\\n\\n"; exit 1; \
	fi

fix-ruff-format:
	@printf "$(CYAN)Ruff format...$(NC)\\n"; (set -x ; uv run ruff format .); \
	if [ $$? -eq 0 ]; then printf "$(GREEN)✅ Ruff format passed!$(NC)\\n\\n"; \
	else printf "$(RED)❌ Ruff format failed!$(NC)\\n\\n"; exit 1; \
	fi

test:
	uv run pytest

upgrade:
	uv sync --upgrade --all-extras

upgrade-dev:
	uv sync --upgrade --all-extras --dev

build:
	uv build

clean:
	-rm -rf dist/
	-rm -rf .venv/
	-find . -type d -name "__pycache__" -exec rm -rf {} +
