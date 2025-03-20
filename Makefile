deps:
	poetry install --all-extras --all-groups
ifeq ($(shell poetry run --no-plugins which ruff),)
	@echo 'Command "ruff" not found! You may need to install it by `pipx install ruff`'
endif

local_test:
	PYTHONPATH=. poetry run pytest tests/

test:
ifeq ($(shell poetry run --no-plugins which mypy),)
	$(MAKE) deps
endif
ifneq ($(shell which docker-compose),)
	docker-compose build test
	docker-compose run test
else
	$(MAKE) local_test
endif

lint:
ifeq ($(shell poetry run --no-plugins which mypy),)
	$(MAKE) deps
endif
ifeq ($(shell poetry run --no-plugins which fast),)
	poetry run fast lint
endif
	poetry run ruff format
	poetry run ruff check --fix
	poetry run mypy .

debug_test:
	docker-compose build test
	docker-compose run test /bin/bash

dist:
	poetry build --clean

upload:
	poetry run fast upload

.PHONY: dist upload test debug_test deps lint
