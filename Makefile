PYTHON = python3
PIP = pip3
NPM = npm

PIPFLAGS=$$([ -z "$$VIRTUAL_ENV" ] && echo --user) -U

.PHONY: test
test:
	$(PYTHON) -m unittest

.PHONY: test-ext
test-ext:
	$(PYTHON) -m unittest discover -p "ext_test*.py"

.PHONY: test-ui
test-ui:
	node_modules/.bin/mocha "**/ui_test*.js"

.PHONY: lint
lint:
	pylint -j 0 meetling micro

.PHONY: check
check: test test-ext lint test-ui

.PHONY: deps
deps:
	$(PIP) install $(PIPFLAGS) -r requirements.txt
	$(NPM) update --prod
	node_modules/.bin/bower update

.PHONY: deps-dev
deps-dev:
	$(PIP) install $(PIPFLAGS) -r requirements-dev.txt
	# there is no --dev
	$(NPM) update

.PHONY: doc
doc:
	sphinx-build doc doc/build

.PHONY: sample
sample:
	scripts/sample.py

.PHONY: help
help:
	@echo "test:     Run all unit tests"
	@echo "test-ext: Run all extended/integration tests"
	@echo "test-ui:  Run all UI tests."
	@echo "lint:     Lint and check the style of the code"
	@echo "check:    Run all code quality checks (test and lint)"
	@echo "deps:     Update the dependencies"
	@echo "deps-dev: Update the development dependencies"
	@echo "doc:      Build the documentation"
	@echo "sample:   Set up some sample data. Warning: All existing data in the database"
	@echo "          will be deleted."
	@echo "          REDISURL: URL of the Redis database. See"
	@echo "                    python3 -m meetling --redis-url command line option."
