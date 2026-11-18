"""Regression checks for documentation of the generated clients."""

import re
import tomllib
from collections.abc import Callable, Iterator
from html import unescape
from pathlib import Path

import griffe
import pytest
from griffe import ParameterKind
from markdown import Markdown
from mkdocstrings_handlers.python import PythonConfig, PythonHandler

from scripts.docs.generate_doc_stubs import DocStubGenerator, StreamType
from scripts.docs.griffe_extensions import MergedOperationSignature, OverloadDocstrings

REPO_ROOT = Path(__file__).resolve().parents[3]


def client_dir(service: str) -> Path:
    return (
        REPO_ROOT
        / "clients"
        / f"aws-sdk-{service}"
        / "src"
        / f"aws_sdk_{service.replace('-', '_')}"
    )


def text_of(html: str) -> str:
    """Return rendered HTML as plain text, without highlight markup."""
    return unescape(re.sub(r"<[^>]+>", "", html))


def rendered_signatures(html: str, name: str) -> list[str]:
    """Return the signatures rendered for a function."""
    signatures = re.findall(rf"{name}\(.*?\) ->", text_of(html), re.S)
    return [re.sub(r"\s+", " ", signature) for signature in signatures]


def write_client_package(root: Path, sync_client: str, async_client: str) -> Path:
    """Write a minimal dual-mode client package with the given client bodies."""
    package = root / "aws_sdk_fake"
    (package / "aio").mkdir(parents=True)
    (package / "__init__.py").write_text("")
    (package / "aio" / "__init__.py").write_text("")
    (package / "models.py").write_text(
        "from dataclasses import dataclass\n"
        "from typing import TypedDict\n"
        "@dataclass\n"
        "class PingInput: ...\n"
        "class PingInputDict(TypedDict): ...\n"
        "class OtherInputDict(TypedDict): ...\n"
        "@dataclass\n"
        "class PingOutput: ...\n"
        "@dataclass\n"
        "class OtherOutput: ...\n"
    )
    config = (
        "from collections.abc import Callable\n"
        "from typing import TypeAlias\n"
        "class {prefix}FakeConfig: ...\n"
        "Plugin: TypeAlias = Callable[[{prefix}FakeConfig], None]\n"
    )
    (package / "config.py").write_text(config.format(prefix=""))
    (package / "aio" / "config.py").write_text(config.format(prefix="Async"))
    models = "PingInput, PingInputDict, OtherInputDict, PingOutput, OtherOutput"
    (package / "client.py").write_text(
        f"from .models import {models}\nclass FakeClient:\n{sync_client}"
    )
    (package / "aio" / "client.py").write_text(
        f"from ..models import {models}\nclass AsyncFakeClient:\n{async_client}"
    )
    return package


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
    # Symbol pages aren't in the navigation, so they carry the theme's path markup.
    assert page.startswith('<nav class="md-path" aria-label="Navigation" markdown>\n')
    assert (
        '[<span class="md-ellipsis">Operations</span>](../index.md#operations)'
        "{ .md-path__link }"
    ) in page
    assert f"::: {operation.module_path}" in page
    if stream_type:
        # Event streams are only available on the async client.
        assert operation.sync_module_path is None
        assert '!!! info "Async only"' in page
        assert '=== "Sync"' not in page
    else:
        assert operation.sync_module_path == operation.module_path.replace(
            ".aio.client.Async", ".client."
        )
        assert (
            page.index('=== "Sync"')
            < page.index(f"    ::: {operation.sync_module_path}")
            < page.index('=== "Async"')
            < page.index(f"    ::: {operation.module_path}")
            < page.index("## Input")
        )
    # The dictionaries and the model share their fields, so they are tabs, and
    # the Dictionary tab, first, holds every dictionary the operation accepts.
    assert "### Dictionaries" not in page
    assert "### Model" not in page
    input_section = page[page.index("## Input") : page.index("## Output")]
    dictionary_tab = input_section.index('=== "Dictionary"')
    model_tab = input_section.index('=== "Model"')
    for dictionary in operation.input_dicts:
        assert (
            dictionary_tab
            < input_section.index(f"    ::: {dictionary.module_path}\n")
            < model_tab
        )
    assert model_tab < input_section.index(f"    ::: {operation.input.module_path}\n")
    assert (
        "Pass the input as keyword arguments, a positional dictionary, or a "
        "positional model object."
    ) in page
    for name in (operation.event_input_type, operation.event_output_type):
        if name:
            assert any(union.name == name for union in client.models.unions)


def test_index_documents_both_client_modes(tmp_path: Path) -> None:
    generator = DocStubGenerator(client_dir("bedrock-runtime"), tmp_path)
    client = generator._analyze_client_package("aws_sdk_bedrock_runtime")
    generator._generate_index(client)
    index = (tmp_path / "index.md").read_text()

    client_section = index.split("## Client")[1].split("## Operations")[0]
    config_section = index.split("## Configuration")[1].split("## Structures")[0]
    for section, sync_path, async_path in [
        (
            client_section,
            client.sync.client.module_path,
            client.async_.client.module_path,
        ),
        (
            config_section,
            client.sync.config.module_path,
            client.async_.config.module_path,
        ),
    ]:
        assert (
            section.index('=== "Sync"')
            < section.index(f"    ::: {sync_path}")
            < section.index('=== "Async"')
            < section.index(f"    ::: {async_path}")
        )
    assert client.sync.client.module_path.endswith(".client.BedrockRuntimeClient")
    assert client.async_.config.module_path.endswith(
        ".aio.config.AsyncBedrockRuntimeConfig"
    )
    assert "merge_init_into_class: true" in client_section
    assert "merge_init_into_class" not in config_section
    # Both modes export a Plugin alias, so the table of contents tells them apart.
    assert 'toc_label: "Plugin (Sync)"' in config_section
    assert 'toc_label: "Plugin (Async)"' in config_section

    assert "available only on `AsyncBedrockRuntimeClient`" in client_section
    assert (
        "- [`converse_stream`](operations/converse_stream.md) "
        '<span class="mode-badge">Async only</span>\n'
    ) in index
    assert "- [`converse`](operations/converse.md)\n" in index

    # Bidirectional streams need the CRT transport, so installation covers it.
    installation = index.split("## Installation")[1].split("## Client")[0]
    assert "\n### Bidirectional streaming\n" in installation
    assert 'python -m pip install "aws-sdk-bedrock-runtime[awscrt]"' in installation
    assert "pass an `AWSCRTHTTPClient` instance as the transport" in installation

    sts = DocStubGenerator(client_dir("sts"), tmp_path / "sts")
    sts._generate_index(sts._analyze_client_package("aws_sdk_sts"))
    sts_index = (tmp_path / "sts" / "index.md").read_text()
    assert "available only on" not in sts_index
    assert "mode-badge" not in sts_index
    assert "Bidirectional streaming" not in sts_index


def test_dictionaries_only_the_async_client_accepts_are_named(tmp_path: Path) -> None:
    generator = DocStubGenerator(client_dir("s3"), tmp_path)
    client = generator._analyze_client_package("aws_sdk_s3")
    operations = {op.name: op for op in client.operations}
    put_object, get_object = operations["put_object"], operations["get_object"]
    assert [d.name for d in put_object.async_only_input_dicts] == [
        "AsyncPutObjectInputDict"
    ]
    assert get_object.async_only_input_dicts == []

    generator._generate_operation_stubs([put_object, get_object])
    put_page = (tmp_path / "operations" / "put_object.md").read_text()
    assert (
        "Both clients accept `PutObjectInputDict`. Only the asynchronous client "
        "accepts `AsyncPutObjectInputDict`."
    ) in put_page
    get_page = (tmp_path / "operations" / "get_object.md").read_text()
    assert "Only the asynchronous client accepts" not in get_page


ASYNC_PING = (
    "    async def ping(self, input: PingInput | PingInputDict) -> PingOutput: ...\n"
)


@pytest.mark.parametrize(
    ("sync_client", "error"),
    [
        (
            "    def ping(self, input: PingInput | PingInputDict) -> OtherOutput: ...\n",
            "sync and async return types differ",
        ),
        (
            "    def ping(self, input: PingInput | OtherInputDict) -> PingOutput: ...\n",
            "not a subset of the async input types",
        ),
        (
            "    def pong(self, input: PingInput | PingInputDict) -> PingOutput: ...\n",
            "Operations missing from AsyncFakeClient: pong",
        ),
    ],
)
def test_sync_operations_must_match_their_async_counterparts(
    tmp_path: Path, sync_client: str, error: str
) -> None:
    """Both clients share one page per operation, so their types must agree."""
    package = write_client_package(tmp_path, sync_client, ASYNC_PING)
    generator = DocStubGenerator(package, tmp_path / "docs")
    with pytest.raises(ValueError, match=error):
        generator._analyze_client_package(package.name)


def test_matching_sync_operation_is_documented(tmp_path: Path) -> None:
    sync_ping = (
        "    def ping(self, input: PingInput | PingInputDict) -> PingOutput: ...\n"
    )
    package = write_client_package(tmp_path, sync_ping, ASYNC_PING)
    generator = DocStubGenerator(package, tmp_path / "docs")
    client = generator._analyze_client_package(package.name)
    [operation] = client.operations
    assert operation.sync_module_path == "aws_sdk_fake.client.FakeClient.ping"
    assert operation.module_path == "aws_sdk_fake.aio.client.AsyncFakeClient.ping"
    assert operation.async_only_input_dicts == []


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


@pytest.fixture(scope="module")
def render() -> Iterator[Callable[..., str]]:
    """Render an object with the site's mkdocstrings options plus any overrides."""
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
    handler._update_env(Markdown(extensions=["pymdownx.highlight", "toc"]))

    def render(identifier: str, **overrides: object) -> str:
        options = handler.get_options({**python_config["options"], **overrides})
        return handler.render(handler.collect(identifier, options), options)

    try:
        yield render
    finally:
        handler.teardown()


def test_overload_docstrings_are_rendered_with_public_signatures(
    render: Callable[..., str],
) -> None:
    html = render("aws_sdk_dynamodb.aio.client.AsyncDynamoDBClient.list_tables")
    # One signature that covers the request object and keyword arguments.
    assert rendered_signatures(html, "list_tables") == [
        "list_tables(request: ListTablesInput | ListTablesInputDict | None = None, "
        "/, *, plugins: list[Plugin] | None = None, "
        "**kwargs: Unpack[ListTablesInputDict]) ->"
    ]
    parameters = text_of(html).split("Parameters:")[1].split("Returns:")[0]
    for name in ("request", "plugins", "**kwargs"):
        assert name in parameters
    assert "Pass this or keyword" in parameters
    assert "Returns an array of table names" in html
    assert "ListTablesInputDict" in html
    assert "plugins" in html
    assert "kwargs" in html
    assert "*args" not in html
    sync_html = render("aws_sdk_dynamodb.client.DynamoDBClient.list_tables")
    assert len(rendered_signatures(sync_html, "list_tables")) == 1
    assert "**kwargs" in text_of(sync_html).split("Parameters:")[1]
    assert "Returns an array of table names" in sync_html
    assert "ListTablesInputDict" in sync_html
    assert "*args" not in sync_html
    dictionary_html = render("aws_sdk_dynamodb.models.ListTablesInputDict")
    assert "exclusive_start_table_name" in dictionary_html
    assert "limit" in dictionary_html


@pytest.mark.parametrize(
    ("client", "config"),
    [
        (
            "aws_sdk_dynamodb.client.DynamoDBClient",
            "aws_sdk_dynamodb.config.DynamoDBConfig",
        ),
        (
            "aws_sdk_dynamodb.aio.client.AsyncDynamoDBClient",
            "aws_sdk_dynamodb.aio.config.AsyncDynamoDBConfig",
        ),
    ],
)
def test_clients_show_their_constructor_and_configs_do_not(
    render: Callable[..., str], client: str, config: str
) -> None:
    # Mirror the options the generated index page uses for each directive.
    client_text = text_of(render(client, members=False, merge_init_into_class=True))
    client_name, config_name = client.rsplit(".", 1)[1], config.rsplit(".", 1)[1]
    assert (
        f"{client_name}(config: {config_name} | None = None, "
        "plugins: list[Plugin] | None = None)"
    ) in client_text
    # Configs are built with resolve(); calling the class directly raises.
    config_text = text_of(render(config))
    assert f"{config_name}(" not in config_text
    assert "resolve(" in config_text


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


def test_operation_overloads_merge_into_one_signature(tmp_path: Path) -> None:
    source = tmp_path / "fake_operations.py"
    source.write_text(
        "from typing import TypedDict, Unpack, overload\n"
        "class InputDict(TypedDict): ...\n"
        "class Client:\n"
        "    @overload\n"
        "    def operation(self, request: InputDict, /, *, plugins: list | None = None) -> int:\n"
        '        """Operation description.\n\n'
        "        Args:\n"
        "            plugins:\n"
        "                Plugins for this call.\n\n"
        "        Returns:\n"
        '            A number.\n        """\n'
        "    @overload\n"
        "    def operation(self, *, plugins: list | None = None, **kwargs: Unpack[InputDict]) -> int: ...\n"
        "    def operation(self, *args, plugins=None, **kwargs): ...\n"
        "    @overload\n"
        "    def other(self, value: int) -> int: ...\n"
        "    @overload\n"
        "    def other(self, value: str) -> str: ...\n"
        "    def other(self, value): ...\n"
    )
    module = griffe.load(
        source.stem,
        search_paths=[tmp_path],
        extensions=griffe.load_extensions(OverloadDocstrings, MergedOperationSignature),
    )
    operation = module["Client.operation"]
    assert operation.overloads is None
    assert [
        (p.name, p.kind, str(p.annotation), p.default) for p in operation.parameters
    ] == [
        ("self", ParameterKind.positional_or_keyword, "None", None),
        ("request", ParameterKind.positional_only, "InputDict | None", "None"),
        ("plugins", ParameterKind.keyword_only, "list | None", "None"),
        ("kwargs", ParameterKind.var_keyword, "Unpack[InputDict]", "{}"),
    ]
    assert str(operation.returns) == "int"
    # The description came from the request overload, and the Args section now
    # documents every way to pass the input, in signature order.
    sections = operation.docstring.parse("google")
    assert sections[0].value == "Operation description."
    [args] = [section for section in sections if section.kind.value == "parameters"]
    assert [p.name for p in args.value] == ["request", "plugins", "**kwargs"]
    assert any(section.kind.value == "returns" for section in sections)
    # Functions that aren't generated operations keep their overloads.
    assert len(module["Client.other"].overloads) == 2
