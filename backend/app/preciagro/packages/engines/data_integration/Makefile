PYTHON ?= python

# Ensure the monorepo root is on the import path when running local commands.
export PYTHONPATH := ../../../..

.PHONY: install format lint type test run audit

install:
	$(PYTHON) -m pip install -r ../../../../requirements.txt

format:
	$(PYTHON) -m black . && $(PYTHON) -m isort .

lint:
	$(PYTHON) -m ruff check . || $(PYTHON) -m flake8 .

type:
	$(PYTHON) -m mypy .

test:
	$(PYTHON) -m pytest tests -q

run:
	@echo "Run the FastAPI service via: uvicorn preciagro.apps.api_gateway.main:app --host 0.0.0.0 --port 8101 --reload"

audit:
	$(PYTHON) -m pip install --quiet pip-audit
	$(PYTHON) -m pip_audit
