JUST ?= just

deps:
	$(JUST) deps $(options)

venv:
	$(JUST) venv $(options) $(version)

up:
	$(JUST) up

local_test:
	$(JUST) local_test

_test:
	$(JUST) _test

test:
	$(JUST) test

_lint:
	$(JUST) _lint

lint:
	$(JUST) lint

_check:
	$(JUST) _check

check:
	$(JUST) check

debug_test:
	$(JUST) debug_test

dist:
	$(JUST) dist

build:
	$(JUST) build

upload:
	$(JUST) upload

.PHONY: deps venv up local_test _test test _lint lint _check check debug_test dist build upload
