"""Regression checks for documentation of the generated clients."""

import re
import tomllib
from pathlib import Path

import griffe
import pytest
from markdown import Markdown
from mkdocstrings_handlers.python import PythonConfig, PythonHandler

from scripts.docs.generate_doc_stubs import DocStubGenerator, StreamType
from scripts.docs.griffe_extensions import OverloadDocstrings

REPO_ROOT = Path(__file__).resolve().parents[3]


def client_dir(service: str) -> Path:
    return (
        REPO_ROOT
        / "clients"
        / f"aws-sdk-{service}"
        / "src"
        / f"aws_sdk_{service.replace('-', '_')}"
    )


@pytest.mark.parametrize(
    ("service", "operation_name", "stream_type", "dictionary_count"),
    [
        ("dynamodb", "list_tables", None, 1),
        ("ec2", "describe_instances", None, 1),
        ("sts", "assume_role", None, 1),
        ("s3", "put_object", None, 2),
        ("lambda", "invoke_async", None, 2),
        ("lex-runtime-v2", "recognize_utterance", None, 2),
        ("bedrock-runtime", "converse_stream", StreamType.OUTPUT, 1),
        ("transcribe-streaming", "start_stream_transcription", StreamType.DUPLEX, 1),
    ],
)
def test_operation_inputs_and_streams(
    tmp_path: Path,
    service: str,
    operation_name: str,
    stream_type: StreamType | None,
    dictionary_count: int,
) -> None:
    generator = DocStubGenerator(client_dir(service), tmp_path)
    client = generator._analyze_client_package(generator.client_dir.name)
    operation = next(op for op in client.operations if op.name == operation_name)
    assert len(operation.input_dicts) == dictionary_count
    assert operation.input_dicts[0].name == f"{operation.input.name}Dict"
    assert operation.input.module_path.startswith(f"{client.package_name}.models.")
    assert operation.stream_type == stream_type
    generator._generate_operation_stubs([operation])
    page = (tmp_path / "operations" / f"{operation_name}.md").read_text()
    assert f"::: {operation.input.module_path}" in page
    for dictionary in operation.input_dicts:
        assert f"::: {dictionary.module_path}" in page
    assert "keyword arguments" in page
    for name in (operation.event_input_type, operation.event_output_type):
        if name:
            assert any(union.name == name for union in client.models.unions)


def test_partitioned_models_keep_public_paths_and_complete_links(
    tmp_path: Path,
) -> None:
    generator = DocStubGenerator(client_dir("dynamodb"), tmp_path)
    assert generator.service_name == "DynamoDB"
    client = generator._analyze_client_package("aws_sdk_dynamodb")
    assert any(model.name == "TableDescription" for model in client.models.structures)
    assert any(
        model.name == "AttributeDefinitionDict" for model in client.models.dictionaries
    )
    assert any(
        model.name == "ResourceNotFoundException" for model in client.models.errors
    )
    assert any(model.name == "TableStatus" for model in client.models.enums)
    union = next(
        union for union in client.models.unions if union.name == "AttributeValueDict"
    )
    assert any(member.name == "AttributeValueSDict" for member in union.members)
    assert generator._generate_client_docs(client)

    pages = list(tmp_path.rglob("*.md"))
    for page in pages:
        text = page.read_text()
        assert "._private." not in text
        for reference in re.findall(r"\]\(([^)#]+)(?:#[^)]*)?\)", text):
            assert (page.parent / reference).is_file(), (page, reference)
    index = (tmp_path / "index.md").read_text()
    assert "[`ListTablesInputDict`](dictionaries/" not in index
    assert "[`TypedDict`](dictionaries/" not in index


def test_generator_uses_supplied_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An installed package must not shadow the requested client checkout."""
    stale_package = tmp_path / "installed" / "aws_sdk_sts"
    stale_package.mkdir(parents=True)
    (stale_package / "__init__.py").write_text(
        '"""An old installed client without aio."""'
    )
    monkeypatch.syspath_prepend(str(stale_package.parent))
    generator = DocStubGenerator(client_dir("sts"), tmp_path / "docs")
    assert generator.generate()
    assert (tmp_path / "docs" / "operations" / "assume_role.md").is_file()


def test_overload_docstrings_are_rendered_with_public_signatures() -> None:
    config = tomllib.loads((REPO_ROOT / "zensical.toml").read_text())["project"]
    python_config = config["plugins"]["mkdocstrings"]["handlers"]["python"]
    handler = PythonHandler(
        config=PythonConfig.from_data(paths=python_config["paths"]),
        base_dir=REPO_ROOT,
        theme="material",
        custom_templates=None,
        mdx=["pymdownx.highlight", "toc"],
        mdx_config={},
    )
    try:
        handler._update_env(Markdown(extensions=["pymdownx.highlight", "toc"]))
        options = handler.get_options(python_config["options"])
        operation = handler.collect(
            "aws_sdk_dynamodb.aio.client.AsyncDynamoDBClient.list_tables", options
        )
        html = handler.render(operation, options)
        assert "Returns an array of table names" in html
        assert "ListTablesInputDict" in html
        assert "plugins" in html
        assert "kwargs" in html
        assert "*args" not in html
        dictionary = handler.collect(
            "aws_sdk_dynamodb.models.ListTablesInputDict", options
        )
        dictionary_html = handler.render(dictionary, options)
        assert "exclusive_start_table_name" in dictionary_html
        assert "limit" in dictionary_html
    finally:
        handler.teardown()


def test_extension_preserves_existing_docstrings(tmp_path: Path) -> None:
    source = tmp_path / "overloaded.py"
    source.write_text(
        "from typing import overload\n"
        "@overload\n"
        "def documented(value: str) -> str:\n"
        '    """Overload description."""\n'
        "def documented(value):\n"
        '    """Implementation description."""\n'
        "@overload\n"
        "def undocumented(value: str) -> str: ...\n"
        "def undocumented(value): ...\n"
    )
    module = griffe.load(
        source.stem,
        search_paths=[tmp_path],
        extensions=griffe.load_extensions(OverloadDocstrings),
    )
    assert module["documented"].docstring.value == "Implementation description."
    assert module["undocumented"].docstring is None
