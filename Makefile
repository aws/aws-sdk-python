DOCS_PORT ?= 8000
PYTHON_VERSION := 3.12

# Colocated smithy-python checkout that provides the codegen jars.
SMITHY_PYTHON ?= ../smithy-python

.PHONY: docs docs-serve docs-clean docs-install docs-lock venv gen publish-codegen

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
