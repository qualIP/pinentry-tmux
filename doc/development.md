# Development

## Setting Up uv

This project is set up to use [uv](https://docs.astral.sh/uv/) to manage Python and
dependencies. First, be sure you
[have uv installed](https://docs.astral.sh/uv/getting-started/installation/).

Then [fork the qualIP/pinentry-tmux repo](https://github.com/qualIP/pinentry-tmux/fork)
(having your own fork will make it easier to contribute) and
[clone it](https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository).

## Basic Developer Workflows

The `GNUmakefile` simply offers shortcuts to `uv` commands for developer convenience.
(For clarity, GitHub Actions don't use the GNUmakefile and just call `uv` directly.)

```shell
# First, setup your virtual environment, install all development dependencies, and local git hooks.
make dev

# Linting (check mode):
make lint

# Linting (fix mode):
make fix

# Run tests:
make test

# Delete all the build artifacts:
make clean

# Upgrade dependencies to compatible versions:
make upgrade-dev

# To run tests by hand:
uv run pytest   # all tests
uv run pytest -s src/module/some_file.py  # one test, showing outputs

# Build and install current dev executables, to let you use your dev copies
# as local tools:
uv tool install --editable .

# Dependency management directly with uv:
# Add a new dependency:
uv add package_name
# Add a development dependency:
uv add --dev package_name
# Update to latest compatible versions (including dependencies on git repos):
uv sync --upgrade
# Update a specific package:
uv lock --upgrade-package package_name
# Update dependencies on a package:
uv add package_name@latest

# Run a shell within the Python environment:
uv venv
source .venv/bin/activate
```

See [uv docs](https://docs.astral.sh/uv/) for details.

## Commits

We use [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/).

I strongly suggest you use a pre-commit hook to automatically lint your commit changes:

```shell
cat <<EOF > .git/hooks/pre-commit
#!/bin/sh
make lint
EOF
```

If linting fails, the commit will be blocked until you fix the issues, by hand or with `make fix`, `git add` the changes and try again.
You can still temporarily bypass the pre-commit hook with `git commit --no-verify`.

## Agent Rules

See [AGENTS.md](AGENTS.md] and [doc/ai/instructions](doc/ai/instructions) for agent rules.
These are written for any and all agentic software.

## Documentation

- [uv docs](https://docs.astral.sh/uv/)
- [codespell docs](https://github.com/codespell-project/codespell)
- [ruff docs](https://docs.astral.sh/ruff/)
- [basedpyright docs](https://docs.basedpyright.com/latest/)

* * *

*This file was built with
[simple-modern-uv](https://github.com/jlevy/simple-modern-uv).*
