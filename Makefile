deps:
	poetry install --all-extras --all-groups

local_test:
	PYTHONPATH=. pytest tests/

test: deps _test
_test:
ifneq ($(shell which docker-compose),)
	docker-compose build test
	docker-compose run test
else
	$(MAKE) local_test
endif

lint: deps _lint
_lint:
	poetry run fast lint

debug_test:
	docker-compose build test
	docker-compose run test /bin/bash

clean:
	rm -rf dist build *.egg-info

dist: clean
	poetry build

upload:
	poetry run fast upload

.PHONY: dist upload test debug_test deps
