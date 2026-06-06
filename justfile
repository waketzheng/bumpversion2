default:
    @just --list

deps *options:
    uv sync {{ options }} --active --inexact --all-extras --all-groups

venv *args:
    pdm venv create {{ args }}

up:
    uv lock --upgrade --verbose

local_test:
    pdm run pytest tests/

docker_test:
    docker-compose build test
    docker-compose run test

_test:
    python -c "import shutil, subprocess, sys; sys.exit(subprocess.call(['just', 'docker_test' if shutil.which('docker-compose') else 'local_test']))"

test: deps _test

_lint *args:
    ruff format
    ruff check --fix {{args}}
    uv run --no-sync mypy .

lint: deps _lint

_check:
    ruff format --check
    ruff check
    uv run --no-sync mypy .
    just --fmt --check

check: deps _check local_test

debug_test:
    docker-compose build test
    docker-compose run test /bin/bash

dist *args:
    uv build --clear {{args}}

build *args: deps
    @just dist {{args}}

upload: dist
    pdm run fast upload
