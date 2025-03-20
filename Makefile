test:
	docker-compose build test
	docker-compose run test

local_test:
	PYTHONPATH=. pytest tests/

lint:
	poetry run fast lint

debug_test:
	docker-compose build test
	docker-compose run test /bin/bash

clean:
	rm -rf dist build *.egg-info

dist:	clean
	poetry build

upload:
	twine upload dist/*

.PHONY: dist upload test debug_test
