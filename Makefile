DOCS_PORT ?= 8000
PYTHON_VERSION := 3.12

# Colocated smithy-python checkout that provides the codegen jars.
SMITHY_PYTHON ?= ../smithy-python

# Clients per gradle build in `make clients`; lower it if the build runs out of heap.
BATCH_SIZE ?= 25

.PHONY: docs docs-serve docs-clean docs-install docs-lock venv gen clients publish-codegen aio-check

# Publishes the smithy-python codegen jars to the local Maven cache so `gen`
# can resolve them. Run once, and again whenever the generator changes.
publish-codegen:
	cd $(SMITHY_PYTHON)/codegen && ./gradlew :core:publishToMavenLocal :aws:core:publishToMavenLocal

# Regenerate one client from its service model: `make gen dynamodb`.
# Accepts dynamodb, aws_sdk_dynamodb, aws-sdk-dynamodb, or a hyphenated model name.
gen:
	SMITHY_PYTHON=$(abspath $(SMITHY_PYTHON)) uv run python codegen/gen_client.py $(filter-out gen,$(MAKECMDGOALS))

# Regenerate every client from codegen/aws-models with codegen built from the
# smithy-python commit in codegen/smithy-python.toml. Each client is cleared first,
# keeping only the paths in gen_client.py's KEEP, then scripts/client-overlays is applied.
clients:
	SMITHY_PYTHON=$(abspath $(SMITHY_PYTHON)) uv run python codegen/gen_client.py --all --pinned --batch-size $(BATCH_SIZE)

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
