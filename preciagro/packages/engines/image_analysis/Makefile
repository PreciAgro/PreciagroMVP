PACKAGE_DIR := preciagro/packages/engines/image_analysis

.PHONY: install lint format type test check

install:
	pip install -r $(PACKAGE_DIR)/requirements.txt

lint:
	ruff check $(PACKAGE_DIR)

format:
	ruff format $(PACKAGE_DIR)

type:
	mypy $(PACKAGE_DIR)/app

test:
	pytest $(PACKAGE_DIR)/tests -q

check: lint type test
