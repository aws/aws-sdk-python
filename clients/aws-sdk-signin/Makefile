DOCS_PORT ?= 8000
CLIENT_DIR := src/aws_sdk_signin
DOCS_OUTPUT_DIR := docs/client
PYTHON_VERSION := 3.12

.PHONY: docs docs-serve docs-clean docs-install venv

venv:
	uv venv --python $(PYTHON_VERSION)

docs-install: venv
	uv pip install -e . --group docs

docs-clean:
	rm -rf site $(DOCS_OUTPUT_DIR)

docs-generate:
	uv run --no-sync python scripts/docs/generate_doc_stubs.py -c $(CLIENT_DIR) -o $(DOCS_OUTPUT_DIR)

docs: docs-generate
	uv run --no-sync zensical build

docs-serve:
	@[ -d site ] || $(MAKE) docs
	uv run --no-sync python -m http.server $(DOCS_PORT) --bind 127.0.0.1 --directory site
