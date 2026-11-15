DOCS_PORT ?= 8000
PYTHON_VERSION := 3.12

# Colocated smithy-python checkout that provides the codegen jars.
SMITHY_PYTHON ?= ../smithy-python

# Clients per gradle build in `make clients`; lower it if the build runs out of heap.
BATCH_SIZE ?= 25

.PHONY: docs docs-serve docs-clean docs-install docs-lock venv gen clients fragments publish-codegen aio-check meta-package-check static-analysis test-unit test-functional test-integration \
	check-imports check-conventions check-api check-dependencies check-packaging check-import-stability verify-venv api-snapshot \
	canonical-imports dunder-all source-order dynamic-imports banned-imports docstrings declared-deps import-cycles \
	dep-specifiers package-metadata package-metadata-fix version-consistency export-names exception-hierarchy secret-repr import-hygiene \
	import-deprecations import-side-effects import-cost wheel-contents type-completeness optional-deps lowest-bounds

# Each client and package runs in its own .venv. Dependencies outside this repo,
# including smithy-python, resolve from PyPI at the versions each one declares.
PROJECTS := $(patsubst %/pyproject.toml,%,$(wildcard clients/*/pyproject.toml packages/*/pyproject.toml))
RUFF_VERSION := 0.15.22
PYRIGHT_VERSION := 1.1.406
UV_RUN = uv run --python $(PYTHON_VERSION) --project

# The verifications import, build and inspect every client and package together,
# so they share one venv holding all of them editable, plus the pinned tools.
# CAUTION: defined before any rule, since make expands prerequisites as it reads each rule.
VERIFY_VENV := .venv-verify
VERIFY_STAMP := $(VERIFY_VENV)/.installed
VERIFY = $(VERIFY_VENV)/bin/python scripts/verifications

# Q Business is sunsetting; new application creation is unavailable.
INTEGRATION_SKIP := clients/aws-sdk-qbusiness

static-analysis:
	$(MAKE) meta-package-check
	@set -e; for p in $(PROJECTS); do \
		dirs=$$(ls -d $$p/src $$p/tests 2>/dev/null || true); \
		group=$$(grep -q '^test = \[' $$p/pyproject.toml && echo --group test || true); \
		echo "== $$p"; \
		uvx ruff@$(RUFF_VERSION) check --config $$p/pyproject.toml $$dirs; \
		uvx ruff@$(RUFF_VERSION) format --check --config $$p/pyproject.toml $$dirs; \
		$(UV_RUN) $$p $$group --with pyright==$(PYRIGHT_VERSION) pyright -p $$p $$dirs; \
	done
	$(MAKE) aio-check
	$(MAKE) check-imports
	$(MAKE) check-conventions
	$(MAKE) check-api
	$(MAKE) check-dependencies
	$(MAKE) check-packaging
	$(MAKE) check-import-stability

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

# Only for a smithy-python pointer move: writes a changelog fragment from
# CODEGEN_SYNC_CHANGELOG.md for every generated client.
fragments:
	uv run --no-project --python $(PYTHON_VERSION) python codegen/gen_fragments.py

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
aio-check: $(VERIFY_STAMP)
	$(VERIFY_VENV)/bin/python scripts/aio-naming/aio_naming.py

# Catches a client missing from aws-sdk-python's extras or in-repo sources, which
# would otherwise resolve from PyPI and fail on any unpublished version bump.
meta-package-check:
	uv run --no-project --python $(PYTHON_VERSION) python scripts/meta-package/meta_package.py

check-imports: ## Keeps the import graph explicit, acyclic, and free of test-only modules.
	$(MAKE) canonical-imports
	$(MAKE) import-cycles
	$(MAKE) dynamic-imports
	$(MAKE) banned-imports

check-conventions: ## Holds shipped code to our ordering, docstring, error, and secret-handling conventions.
	$(MAKE) source-order
	$(MAKE) docstrings
	$(MAKE) exception-hierarchy
	$(MAKE) secret-repr

check-api: ## Keeps the public API surface reviewed, typed, and exported under its own names.
	$(MAKE) api-snapshot
	$(MAKE) export-names
	$(MAKE) dunder-all
	$(MAKE) type-completeness

check-dependencies: ## Keeps declared dependencies honest for customers who install only some packages.
	$(MAKE) declared-deps
	$(MAKE) dep-specifiers
	$(MAKE) optional-deps
	$(MAKE) lowest-bounds

check-packaging: ## Keeps what we publish to PyPI consistent across packages.
	$(MAKE) package-metadata
	$(MAKE) version-consistency
	$(MAKE) wheel-contents

check-import-stability: ## Keeps importing our packages cheap and free of side effects.
	$(MAKE) import-hygiene
	$(MAKE) import-deprecations
	$(MAKE) import-side-effects
	$(MAKE) import-cost

$(VERIFY_STAMP): $(addsuffix /pyproject.toml,$(PROJECTS))
	uv venv --allow-existing --quiet --python $(PYTHON_VERSION) $(VERIFY_VENV)
	uv pip install --quiet --python $(VERIFY_VENV)/bin/python --all-extras \
		packaging==25.0 ruff==$(RUFF_VERSION) pyright==$(PYRIGHT_VERSION) \
		$(foreach p,$(PROJECTS),-e $(p) -r $(p)/pyproject.toml)
	touch $@

api-snapshot: $(VERIFY_STAMP) ## Records the public API surface and dual-mode mirrors of each package and asserts no git diff.
	$(VERIFY_VENV)/bin/python scripts/api-snapshot/api_snapshot.py

verify-venv: $(VERIFY_STAMP) ## Installs every client and package into the shared verification venv.

canonical-imports: $(VERIFY_STAMP) ## Prevents re-export imports, which hide where symbols live and invite cycles.
	$(VERIFY)/canonical_imports.py

dunder-all: $(VERIFY_STAMP) ## Keeps __all__ in sync with the public surface that type checkers and docs read.
	$(VERIFY)/dunder_all.py

source-order: $(VERIFY_STAMP) ## Keeps the public API at the top of every file and class.
	$(VERIFY)/source_order.py

dynamic-imports: $(VERIFY_STAMP) ## Keeps every import visible to static tools.
	$(VERIFY)/dynamic_imports.py

banned-imports: $(VERIFY_STAMP) ## Keeps test-only modules out of shipped code.
	$(VERIFY)/banned_imports.py

docstrings: $(VERIFY_STAMP) ## Keeps the public API documented in editors and the API reference.
	$(VERIFY)/docstrings.py

declared-deps: $(VERIFY_STAMP) ## Catches imports that only work because something else installed the dependency.
	$(VERIFY)/declared_deps.py

import-cycles: $(VERIFY_STAMP) ## Catches cycles that make import success depend on import order.
	$(VERIFY)/import_cycles.py

dep-specifiers: $(VERIFY_STAMP) ## Keeps packages co-installable and in-repo version bounds current.
	$(VERIFY)/dep_specifiers.py

package-metadata: $(VERIFY_STAMP) ## Catches pyproject.toml drift between packages.
	$(VERIFY)/package_metadata.py

package-metadata-fix: $(VERIFY_STAMP) ## Repairs canonical classifiers and LICENSE files that package-metadata flags.
	$(VERIFY)/package_metadata.py --fix

version-consistency: $(VERIFY_STAMP) ## Keeps __version__ truthful for user agents and bug reports.
	$(VERIFY)/version_consistency.py

export-names: $(VERIFY_STAMP) ## Catches objects exported under a name other than their own.
	$(VERIFY)/export_names.py

exception-hierarchy: $(VERIFY_STAMP) ## Lets customers catch every SDK error with one except clause.
	$(VERIFY)/exception_hierarchy.py

secret-repr: $(VERIFY_STAMP) ## Keeps credentials out of logs and tracebacks.
	$(VERIFY)/secret_repr.py

import-hygiene: $(VERIFY_STAMP) ## Catches modules that only import after a sibling has warmed sys.modules.
	$(VERIFY)/import_hygiene.py

import-deprecations: $(VERIFY_STAMP) ## Catches removals that Python or a dependency has already scheduled.
	$(VERIFY)/import_deprecations.py

import-side-effects: $(VERIFY_STAMP) ## Keeps imports from overriding the host application's global state.
	$(VERIFY)/import_side_effects.py

import-cost: $(VERIFY_STAMP) ## Catches growth in how many of our modules an import loads.
	$(VERIFY)/import_cost.py

wheel-contents: $(VERIFY_STAMP) ## Catches wheels that miss source or py.typed, or that ship tests.
	$(VERIFY)/wheel_contents.py

type-completeness: $(VERIFY_STAMP) ## Verifies the py.typed promise as a customer's type checker sees it.
	$(VERIFY)/type_completeness.py

optional-deps: $(VERIFY_STAMP) ## Checks that a minimal install without extras works or fails clearly.
	$(VERIFY)/optional_deps.py

lowest-bounds: $(VERIFY_STAMP) ## Proves the declared lower bounds actually work.
	$(VERIFY)/lowest_bounds.py

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
	# The rendered-page cache does not track Python sources read by mkdocstrings.
	uv run zensical build --clean

docs-serve:
	@[ -d site ] || $(MAKE) docs
	uv run python -m http.server $(DOCS_PORT) --bind 127.0.0.1 --directory site
