PYTHON := uv run

.PHONY: sync lint type test all fix

sync:
	uv lock && uv sync

lint:
	$(PYTHON) ruff check . && $(PYTHON) ruff format --check .

fix:
	$(PYTHON) ruff check --fix . && $(PYTHON) ruff format .

type:
	$(PYTHON) pytype -V 3.11 youtube_dump

test:
	$(PYTHON) -m pytest -q

all: fix type test
