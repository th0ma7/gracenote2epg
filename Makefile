# Makefile for gracenote2epg development
# Provides convenient shortcuts for common development tasks

.PHONY: help clean autofix format lint test-unit tests test-one golden-update test test-basic test-full geodata build install-dev check-deps show-dist all

# Default target
help:
	@echo "gracenote2epg development Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  help         Show this help message"
	@echo "  clean        Clean all build artifacts and caches"
	@echo "  autofix      Auto-fix imports and common issues with autoflake"
	@echo "  format       Format code with black"
	@echo "  lint         Run linting with flake8"
	@echo "  test-unit    Run unit tests (stdlib unittest, no extra deps)"
	@echo "  tests        Alias for test-unit"
	@echo "  test-one     Run one test module: make test-one T=test_worker_pool"
	@echo "  golden-update Regenerate the XMLTV golden file (after an intended format change)"
	@echo "  test-basic   Basic functionality test"
	@echo "  test-full    Full distribution test"
	@echo "  test         Alias for test-full"
	@echo "  geodata      Regenerate the bundled postal dataset (run before a release, then commit)"
	@echo "  build        Build distributions (wheel and source)"
	@echo "  install-dev  Install in development mode"
	@echo "  check-deps   Check and install development dependencies"
	@echo "  show-dist    Show current distribution files"
	@echo "  all          Run clean, autofix, format, lint, and test-full"
	@echo ""
	@echo "Examples:"
	@echo "  make clean && make test-basic    # Quick development cycle"
	@echo "  make autofix format lint         # Code quality pipeline"
	@echo "  make all                         # Complete validation"
	@echo "  make build && make show-dist     # Build and inspect"

# Development workflow
clean:
	@chmod +x scripts/dev-helper.bash
	@./scripts/dev-helper.bash clean

autofix:
	@chmod +x scripts/dev-helper.bash
	@./scripts/dev-helper.bash autofix

format:
	@chmod +x scripts/dev-helper.bash
	@./scripts/dev-helper.bash format

lint:
	@chmod +x scripts/dev-helper.bash
	@./scripts/dev-helper.bash lint

test-unit:
	@python3 -m unittest discover -s tests -p "test_*.py" -v

# Alias — `make tests` runs the full stdlib unittest suite.
tests: test-unit

# Run a single test module, e.g. `make test-one T=test_worker_pool`
# (T may also be a class or method path, e.g. test_worker_pool.WallHandlingTests).
test-one:
	@python3 -m unittest -v tests.$(T)

# Regenerate the XMLTV golden file after an INTENTIONAL change to the generator's
# output format; review the diff before committing.
golden-update:
	@python3 -m tests.test_xmltv_golden --update-golden
	@echo "Golden regenerated → review 'git diff tests/fixtures/xmltv_golden.xml' before committing."

test-basic:
	@chmod +x scripts/test-distribution.bash
	@./scripts/test-distribution.bash --basic

test-full:
	@chmod +x scripts/test-distribution.bash
	@./scripts/test-distribution.bash --full

test: test-full

geodata:
	@python3 scripts/build-geodata.py
	@echo "Now review and commit gracenote2epg/data/geopostal.csv.gz"

build:
	@python3 -m build

install-dev:
	@chmod +x scripts/dev-helper.bash
	@./scripts/dev-helper.bash install-dev

check-deps:
	@chmod +x scripts/dev-helper.bash
	@./scripts/dev-helper.bash check-deps

show-dist:
	@chmod +x scripts/dev-helper.bash
	@./scripts/dev-helper.bash show-dist

# Complete workflow with auto-fixes
all: clean autofix format lint test-unit test-full
	@echo "✅ All development tasks completed successfully!"
