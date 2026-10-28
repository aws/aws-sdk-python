DOCS_PORT ?= 8000
PYTHON_VERSION := 3.12

# Colocated smithy-python checkout that provides the codegen jars.
SMITHY_PYTHON ?= ../smithy-python

.PHONY: docs docs-serve docs-clean docs-install docs-lock venv gen publish-codegen dev-install test test-integration typecheck ruff

# Each client and hand-written package is its own project with its own pytest
# and pyright config, so the check targets run them one at a time.
PROJECTS := $(patsubst %/pyproject.toml,%,$(wildcard clients/*/pyproject.toml packages/*/pyproject.toml))
SMITHY_PACKAGES := aws-sdk-signers smithy-core smithy-json smithy-cbor smithy-xml smithy-aws-core smithy-aws-event-stream smithy-test
VENV_BIN := $(CURDIR)/.venv/bin

# Publishes the smithy-python codegen jars to the local Maven cache so `gen`
# can resolve them. Run once, and again whenever the generator changes.
publish-codegen:
	cd $(SMITHY_PYTHON)/codegen && ./gradlew :core:publishToMavenLocal :aws:core:publishToMavenLocal

# Regenerate one client from its service model: `make gen dynamodb`.
# Accepts dynamodb, aws_sdk_dynamodb, aws-sdk-dynamodb, or a hyphenated model name.
gen:
	SMITHY_PYTHON=$(SMITHY_PYTHON) uv run python codegen/gen_client.py $(filter-out gen,$(MAKECMDGOALS))

# Swallow the client-name argument so make does not treat it as a target.
# Scoped to `gen` so it does not mask typos in unrelated commands.
ifeq (gen,$(firstword $(MAKECMDGOALS)))
$(eval $(filter-out gen,$(MAKECMDGOALS)):;@:)
endif

venv:
	uv venv --python $(PYTHON_VERSION)

# Installs every client and package against the colocated smithy-python
# checkout, so checks run against unreleased runtime changes.
dev-install:
	@[ -d .venv ] || uv venv --python $(PYTHON_VERSION)
	uv pip install --python $(VENV_BIN)/python \
		$(foreach p,$(SMITHY_PACKAGES),-e $(SMITHY_PYTHON)/packages/$(p)) \
		-e "$(SMITHY_PYTHON)/packages/smithy-http[aiohttp,awscrt]" \
		$(foreach p,$(PROJECTS),-e ./$(p)) \
		"pytest>=9.0.1,<10.0.0" "pytest-asyncio>=1.3.0,<1.4.0" \
		"boto3==1.43.120" "boto3-stubs[iam,lexv2-models,s3,sts]==1.43.120" \
		"pyright==1.1.406" "ruff==0.15.22"

test: dev-install
	@failed=; for t in $(wildcard packages/*/tests/unit); do \
		$(VENV_BIN)/python -m pytest -q $$t || failed="$$failed $$t"; \
	done; [ -z "$$failed" ] || { echo "unit tests failed in:$$failed"; exit 1; }

# Requires AWS credentials for the accounts and regions the suites target.
test-integration: dev-install
	@failed=; for p in $(PROJECTS); do \
		[ -d $$p/tests/integration ] || continue; \
		$(VENV_BIN)/python -m pytest -q $$p/tests/integration || failed="$$failed $$p"; \
	done; [ -z "$$failed" ] || { echo "integration tests failed in:$$failed"; exit 1; }

typecheck: dev-install
	@failed=; for p in $(PROJECTS); do \
		dirs=$$(cd $$p && ls -d src tests 2>/dev/null); [ -n "$$dirs" ] || continue; \
		(cd $$p && $(VENV_BIN)/pyright --pythonpath $(VENV_BIN)/python $$dirs) || failed="$$failed $$p"; \
	done; [ -z "$$failed" ] || { echo "typecheck failed in:$$failed"; exit 1; }

ruff: dev-install
	$(VENV_BIN)/ruff check clients packages
	$(VENV_BIN)/ruff format --check clients packages

docs-lock: venv
	uv pip compile requirements-docs.in -o requirements-docs.txt

docs-install: venv
	uv pip install -r requirements-docs.txt
	uv pip install -e clients/*

docs-clean:
	rm -rf site docs/clients

docs-generate:
	uv run python scripts/docs/generate_all_doc_stubs.py
	uv run python scripts/docs/generate_nav.py

docs: docs-generate
	uv run zensical build

docs-serve:
	@[ -d site ] || $(MAKE) docs
	uv run python -m http.server $(DOCS_PORT) --bind 127.0.0.1 --directory site
