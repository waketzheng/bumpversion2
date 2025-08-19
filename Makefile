deps:
	uv sync --all-extras --all-groups
ifeq ($(shell pdm run which ruff),)
	@echo 'Command "ruff" not found! You may need to install it by `pipx install ruff` or `uv tool install ruff`'
endif

local_test:
	PYTHONPATH=. pdm run pytest tests/

_test:
ifneq ($(shell which docker-compose),)
	docker-compose build test
	docker-compose run test
else
	$(MAKE) local_test
endif
test: deps _test

_lint:
	ruff format
	ruff check --fix
	mypy .
lint: deps _lint

debug_test:
	docker-compose build test
	docker-compose run test /bin/bash

dist:
	rm -fR dist/
	uv build

upload:
	pdm run fast upload

.PHONY: dist upload test debug_test deps lint
