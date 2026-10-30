DOCS_PORT ?= 8000
PYTHON_VERSION := 3.12

# Colocated smithy-python checkout that provides the codegen jars.
SMITHY_PYTHON ?= ../smithy-python

# Clients per gradle build in `make clients`; lower it if the build runs out of heap.
BATCH_SIZE ?= 25

.PHONY: docs docs-serve docs-clean docs-install docs-lock venv gen clients publish-codegen aio-check static-analysis test-unit test-functional test-integration

# Each client and package runs in its own .venv. Dependencies outside this repo,
# including smithy-python, resolve from PyPI at the versions each one declares.
PROJECTS := $(patsubst %/pyproject.toml,%,$(wildcard clients/*/pyproject.toml packages/*/pyproject.toml))
RUFF_VERSION := 0.15.22
PYRIGHT_VERSION := 1.1.406
UV_RUN = uv run --python $(PYTHON_VERSION) --project

# Q Business is sunsetting; new application creation is unavailable.
INTEGRATION_SKIP := clients/aws-sdk-qbusiness

static-analysis:
	@set -e; for p in $(PROJECTS); do \
		dirs=$$(ls -d $$p/src $$p/tests 2>/dev/null || true); \
		group=$$(grep -q '^test = \[' $$p/pyproject.toml && echo --group test || true); \
		echo "== $$p"; \
		uvx ruff@$(RUFF_VERSION) check --config $$p/pyproject.toml $$dirs; \
		uvx ruff@$(RUFF_VERSION) format --check --config $$p/pyproject.toml $$dirs; \
		$(UV_RUN) $$p $$group --with pyright==$(PYRIGHT_VERSION) pyright -p $$p $$dirs; \
	done
	# TODO: enable once aws-credentials-sts passes the aio naming rules.
	# $(MAKE) aio-check

test-unit:
	@set -e; for p in $(PROJECTS); do \
		[ -d $$p/tests/unit ] || continue; \
		echo "== $$p"; \
		$(UV_RUN) $$p --group test pytest $$p/tests/unit; \
	done

test-functional:
	# pytest exits 5 when a generated protocol test file has no cases.
	@set -e; for p in $(PROJECTS); do \
		[ -n "$$(find $$p/tests -name 'test_*.py' -not -path '*/tests/unit/*' -not -path '*/tests/integration/*' 2>/dev/null)" ] || continue; \
		echo "== $$p"; \
		$(UV_RUN) $$p --group test pytest $$p/tests --ignore=$$p/tests/unit --ignore=$$p/tests/integration || [ $$? -eq 5 ]; \
	done

# Calls live services, so it needs AWS credentials.
test-integration:
	@set -e; for p in $(filter-out $(INTEGRATION_SKIP),$(PROJECTS)); do \
		[ -d $$p/tests/integration ] || continue; \
		echo "== $$p"; \
		$(UV_RUN) $$p --group test --all-extras pytest $$p/tests/integration; \
	done

# Regenerate every client from codegen/aws-models with codegen built from the
# smithy-python commit in codegen/smithy-python.toml. Each client is cleared first,
# keeping only the paths in gen_client.py's KEEP, then scripts/client-overlays is applied.
clients:
	SMITHY_PYTHON=$(abspath $(SMITHY_PYTHON)) uv run python codegen/gen_client.py --all --pinned --batch-size $(BATCH_SIZE)

########################## Granular targets below ##########################

# Publishes the smithy-python codegen jars to the local Maven cache so `gen`
# can resolve them. Run once, and again whenever the generator changes.
publish-codegen:
	cd $(SMITHY_PYTHON)/codegen && ./gradlew :core:publishToMavenLocal :aws:core:publishToMavenLocal

# Regenerate one client from its service model: `make gen dynamodb`.
# Accepts dynamodb, aws_sdk_dynamodb, aws-sdk-dynamodb, or a hyphenated model name.
gen:
	SMITHY_PYTHON=$(abspath $(SMITHY_PYTHON)) uv run python codegen/gen_client.py $(filter-out gen,$(MAKECMDGOALS))

# Swallow the client-name argument so make does not treat it as a target.
# Scoped to `gen` so it does not mask typos in unrelated commands.
ifeq (gen,$(firstword $(MAKECMDGOALS)))
$(eval $(filter-out gen,$(MAKECMDGOALS)):;@:)
endif

# Enforces aio naming and separation in package and client sources.
aio-check:
	uv run --no-project --python $(PYTHON_VERSION) python scripts/aio-naming/aio_naming.py

venv:
	uv venv --python $(PYTHON_VERSION)

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
