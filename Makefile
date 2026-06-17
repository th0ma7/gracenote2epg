# Makefile for gracenote2epg development
# Provides convenient shortcuts for common development tasks

.PHONY: help clean autofix format lint test-unit tests test-one golden-update test test-basic test-full geodata build install-dev check-deps show-dist all

# Default target. The target list below is generated from the `## ` comment on
# each target, so it can never drift out of sync — just add a `## description`
# when you add a target.
help:  ## Show this help message
	@echo "gracenote2epg development Makefile"
	@echo ""
	@echo "Available targets:"
	@grep -hE '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "} {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Examples:"
	@echo "  make clean && make test-basic    # Quick development cycle"
	@echo "  make autofix format lint         # Code quality pipeline"
	@echo "  make test-one T=test_worker_pool # Run a single test module"
	@echo "  make all                         # Complete validation"

# Development workflow
clean:  ## Clean all build artifacts and caches
	@chmod +x scripts/dev-helper.bash
	@./scripts/dev-helper.bash clean

autofix:  ## Auto-fix imports and common issues with autoflake
	@chmod +x scripts/dev-helper.bash
	@./scripts/dev-helper.bash autofix

format:  ## Format code with black
	@chmod +x scripts/dev-helper.bash
	@./scripts/dev-helper.bash format

lint:  ## Run linting with flake8
	@chmod +x scripts/dev-helper.bash
	@./scripts/dev-helper.bash lint

test-unit:  ## Run unit tests (stdlib unittest, no extra deps)
	@python3 -m unittest discover -s tests -p "test_*.py" -v

tests: test-unit  ## Alias for test-unit

# T may be a module, class, or method path,
# e.g. T=test_worker_pool.WallHandlingTests
test-one:  ## Run one test module: make test-one T=test_worker_pool
	@python3 -m unittest -v tests.$(T)

golden-update:  ## Regenerate the XMLTV golden file (after an intended format change)
	@python3 -m tests.test_xmltv_golden --update-golden
	@echo "Golden regenerated → review 'git diff tests/fixtures/xmltv_golden.xml' before committing."

test-basic:  ## Basic functionality test
	@chmod +x scripts/test-distribution.bash
	@./scripts/test-distribution.bash --basic

test-full:  ## Full distribution test
	@chmod +x scripts/test-distribution.bash
	@./scripts/test-distribution.bash --full

test: test-full  ## Alias for test-full

geodata:  ## Regenerate the bundled postal dataset (run before a release, then commit)
	@python3 scripts/build-geodata.py
	@echo "Now review and commit gracenote2epg/data/geopostal.csv.gz"

build:  ## Build distributions (wheel and source)
	@python3 -m build

install-dev:  ## Install in development mode
	@chmod +x scripts/dev-helper.bash
	@./scripts/dev-helper.bash install-dev

check-deps:  ## Check and install development dependencies
	@chmod +x scripts/dev-helper.bash
	@./scripts/dev-helper.bash check-deps

show-dist:  ## Show current distribution files
	@chmod +x scripts/dev-helper.bash
	@./scripts/dev-helper.bash show-dist

all: clean autofix format lint test-unit test-full  ## Run clean, autofix, format, lint, and all tests
	@echo "✅ All development tasks completed successfully!"
