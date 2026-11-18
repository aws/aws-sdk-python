"""
Generate markdown API Reference stubs for AWS SDK for Python v4 clients.

This script generates markdown stub files for a single client package.
It uses griffe to analyze the Python source and outputs mkdocstrings directives
for the client, operations, models (structures, unions, enums), and errors.
"""

import argparse
import logging
import re
import sys
import tomllib
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TypeGuard

import griffe
from griffe import (
    Alias,
    Attribute,
    Class,
    Expr,
    ExprBinOp,
    ExprName,
    ExprSubscript,
    ExprTuple,
    Function,
    Module,
    Object,
)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s - %(name)s - %(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("generate_doc_stubs")

ENUM_BASE_CLASSES = ("StrEnum", "IntEnum")
ERROR_BASE_CLASSES = ("ServiceError", "ModeledError")
CLIENT_METHOD_NAMES = ("close",)

# Content tab labels. Zensical links tabs that share a label, so a reader's
# choice of mode carries across every page.
SYNC_LABEL = "Sync"
ASYNC_LABEL = "Async"

# Badge and admonition title for operations that only the async client has.
ASYNC_ONLY_LABEL = f"{ASYNC_LABEL} only"

# Content tab labels for an operation's input, linked across pages like the modes.
DICTIONARY_LABEL = "Dictionary"
MODEL_LABEL = "Model"

# The package extra that installs the AWS CRT HTTP client, which bidirectional
# event streams require.
CRT_EXTRA = "awscrt"


class StreamType(Enum):
    """Type of event stream for operations."""

    INPUT = "AsyncInputEventStream"
    OUTPUT = "AsyncOutputEventStream"
    DUPLEX = "AsyncDuplexEventStream"

    @property
    def description(self) -> str:
        """Return a string description for documentation."""
        descriptions = {
            StreamType.INPUT: "an `AsyncInputEventStream` for client-to-server streaming",
            StreamType.OUTPUT: "an `AsyncOutputEventStream` for server-to-client streaming",
            StreamType.DUPLEX: "an `AsyncDuplexEventStream` for bidirectional streaming",
        }
        return descriptions[self]


@dataclass
class TypeInfo:
    """Information about a type (structure, enum, error, config, plugin)."""

    name: str  # e.g., "ConverseOperationOutput"
    module_path: str  # e.g., "aws_sdk_bedrock_runtime.models.ConverseOperationOutput"


@dataclass
class UnionInfo:
    """Information about a union type."""

    name: str
    module_path: str
    members: list[TypeInfo]


@dataclass
class OperationInfo:
    """Information about a client operation."""

    name: str
    module_path: str  # The asynchronous client's method
    sync_module_path: str | None  # None when only the async client has it
    input: TypeInfo
    input_dicts: list[TypeInfo]  # Every dictionary the async client accepts
    async_only_input_dicts: list[TypeInfo]  # Ones the sync client does not accept
    output: TypeInfo
    stream_type: StreamType | None
    event_input_type: str | None  # For input/duplex streams
    event_output_type: str | None  # For output/duplex streams


@dataclass
class ClientMethodInfo:
    """Information about a non-operation client method."""

    name: str
    module_path: str


@dataclass
class ModelsInfo:
    """Information about all modeled types."""

    structures: list[TypeInfo]
    dictionaries: list[TypeInfo]
    unions: list[UnionInfo]
    enums: list[TypeInfo]
    errors: list[TypeInfo]


@dataclass
class ClientModeInfo:
    """The client, config, and plugin for one client mode (sync or async)."""

    label: str  # e.g., "Async"
    client: TypeInfo  # e.g., AsyncBedrockRuntimeClient
    config: TypeInfo
    plugin: TypeInfo
    client_methods: list[ClientMethodInfo]


@dataclass
class ClientInfo:
    """Complete information about a client package."""

    package_name: str  # e.g., "aws_sdk_bedrock_runtime"
    sync: ClientModeInfo
    async_: ClientModeInfo
    operations: list[OperationInfo]
    models: ModelsInfo

    @property
    def modes(self) -> list[ClientModeInfo]:
        """Both client modes, in content tab order."""
        return [self.sync, self.async_]


class DocStubGenerator:
    """Generate markdown API Reference stubs for AWS SDK for Python v4 clients."""

    def __init__(
        self, client_dir: Path, output_dir: Path, service_name: str | None = None
    ) -> None:
        """
        Initialize the documentation generator.

        Args:
            client_dir: Path to the client source directory
            output_dir: Path to the output directory for generated doc stubs
            service_name: Display name for the service (e.g. the Smithy sdkId
                "SNS"). When omitted, falls back to a title-cased derivation of
                the package name, which does not preserve acronym casing.
        """
        self.client_dir = client_dir
        self.output_dir = output_dir
        # Use the explicit override, then the sdkId from the package, then
        # fall back to a title-cased package name (does not keep acronym
        # casing, so "sns" becomes "Sns").
        self.service_name = (
            service_name
            or self._sdk_id_from_package(client_dir)
            or client_dir.name.replace("aws_sdk_", "").replace("_", " ").title()
        )

    @staticmethod
    def _sdk_id_from_package(client_dir: Path) -> str | None:
        """
        Read the authoritative service name (Smithy sdkId) from the package.

        The generated schemas carry the ``aws.api#service`` trait's ``sdkId``
        (e.g. "SNS"), the same field the sidebar navigation uses, so it keeps
        acronym casing that the package name does not.
        Returns None if the file or value is absent.
        """
        private_dir = client_dir / "_private"
        for schemas in [
            private_dir / "schemas.py",
            *sorted(private_dir.glob("schemas_*.py")),
        ]:
            if schemas.is_file():
                match = re.search(r'"sdkId":\s*"([^"]+)"', schemas.read_text())
                if match:
                    return match.group(1)
        return None

    def generate(self) -> bool:
        """
        Generate the documentation stubs to the output directory.

        Returns:
            True if documentation was generated successfully, False otherwise.
        """
        logger.info(f"Generating doc stubs for {self.service_name}...")

        package_name = self.client_dir.name
        client_info = self._analyze_client_package(package_name)
        if not self._generate_client_docs(client_info):
            return False

        logger.info(f"Finished generating doc stubs for {self.service_name}")
        return True

    def _analyze_client_package(self, package_name: str) -> ClientInfo:
        """Analyze a client package using griffe."""
        logger.info(f"Analyzing package: {package_name}")
        package = griffe.load(package_name, search_paths=[self.client_dir.parent])

        required = ("client", "config", "aio.client", "aio.config", "models")
        missing = [name for name in required if not self._has_module(package, name)]
        if missing:
            raise ValueError(
                f"Missing required modules in {package_name}: {', '.join(missing)}"
            )

        sync_mode, sync_class = self._analyze_mode(package, "", SYNC_LABEL)
        async_mode, async_class = self._analyze_mode(package, "aio.", ASYNC_LABEL)

        # Event streams are only available on the async client, so its
        # operations are a superset of the sync client's.
        sync_operations = {op.name: op for op in self._operation_methods(sync_class)}
        operations = [
            self._analyze_operation(op, sync_operations.pop(op.name, None))
            for op in self._operation_methods(async_class)
        ]
        if sync_operations:
            raise ValueError(
                f"Operations missing from {async_class.name}: "
                f"{', '.join(sorted(sync_operations))}"
            )
        models = self._extract_models(package["models"], operations)

        logger.info(
            f"Analyzed {async_class.name}: "
            f"{len(async_mode.client_methods)} client methods, "
            f"{len(operations)} operations "
            f"({sum(op.sync_module_path is None for op in operations)} async only), "
            f"{len(models.structures)} structures, {len(models.errors)} errors, "
            f"{len(models.dictionaries)} dictionaries, "
            f"{len(models.unions)} unions, {len(models.enums)} enums"
        )

        return ClientInfo(
            package_name=package_name,
            sync=sync_mode,
            async_=async_mode,
            operations=operations,
            models=models,
        )

    def _analyze_mode(
        self, package: Object | Alias, prefix: str, label: str
    ) -> tuple[ClientModeInfo, Class]:
        """Find the client, config, and plugin under a mode's module prefix."""
        client_module = package[f"{prefix}client"]
        config_module = package[f"{prefix}config"]

        client_class = self._find_class_with_suffix(client_module, "Client")
        if not client_class:
            raise ValueError(
                f"No class ending with 'Client' found in {client_module.path}"
            )

        config_class = self._find_class_with_suffix(config_module, "Config")
        if not config_class:
            raise ValueError(
                f"No class ending with 'Config' found in {config_module.path}"
            )

        plugin_alias = config_module.members.get("Plugin")
        if not plugin_alias:
            raise ValueError(f"Missing Plugin in {config_module.path}")

        mode = ClientModeInfo(
            label=label,
            client=TypeInfo(name=client_class.name, module_path=client_class.path),
            config=TypeInfo(name=config_class.name, module_path=config_class.path),
            plugin=TypeInfo(name=plugin_alias.name, module_path=plugin_alias.path),
            client_methods=self._extract_client_methods(client_class),
        )
        return mode, client_class

    def _has_module(self, package: Object | Alias, dotted_name: str) -> bool:
        try:
            return isinstance(package[dotted_name], Module)
        except KeyError:
            return False

    def _find_class_with_suffix(self, module: Module, suffix: str) -> Class | None:
        """Find the class defined in the module with a matching suffix."""
        for cls in module.classes.values():
            # Skip imported classes so a same-package import (e.g. a *Config
            # class re-exported from config.py) can't shadow the defined one.
            if cls.is_imported:
                continue
            if cls.name.endswith(suffix):
                return cls
        return None

    def _operation_methods(self, client_class: Class) -> list[Function]:
        """Return the client methods that are service operations."""
        return [
            op
            for op in client_class.functions.values()
            if not (
                op.is_private
                or op.is_init_method
                or op.is_special
                or op.name in CLIENT_METHOD_NAMES
            )
        ]

    def _extract_client_methods(self, client_class: Class) -> list[ClientMethodInfo]:
        """Extract public client methods that are not service operations."""
        return [
            ClientMethodInfo(name=method.name, module_path=method.path)
            for method in client_class.functions.values()
            if not method.is_private and method.name in CLIENT_METHOD_NAMES
        ]

    def _analyze_operation(
        self, operation: Function, sync_operation: Function | None
    ) -> OperationInfo:
        """Analyze an async operation method and its sync counterpart, if any."""
        stream_type = None
        event_input_type = None
        event_output_type = None

        input_info, input_dicts = self._input_types(operation)
        returns = self._get_expr(operation.returns, f"'{operation.name}' return type")
        async_only_input_dicts = []
        if sync_operation:
            # The page documents one input and output for both clients, so the
            # sync method may differ only by accepting fewer dictionaries.
            sync_input, sync_dicts = self._input_types(sync_operation)
            if sync_input != input_info or any(
                d not in input_dicts for d in sync_dicts
            ):
                raise ValueError(
                    f"'{operation.name}': sync input types are not a subset of "
                    "the async input types"
                )
            sync_returns = self._get_expr(
                sync_operation.returns, f"'{operation.name}' return type"
            )
            if sync_returns.canonical_path != returns.canonical_path:
                raise ValueError(
                    f"'{operation.name}': sync and async return types differ"
                )
            async_only_input_dicts = [d for d in input_dicts if d not in sync_dicts]

        output_type = returns.canonical_name
        stream_type_map = {s.value: s for s in StreamType}

        if output_type in stream_type_map:
            stream_type = stream_type_map[output_type]
            stream_args = self._get_subscript_elements(
                returns, f"'{operation.name}' stream type"
            )

            if stream_type in (StreamType.INPUT, StreamType.DUPLEX):
                event_input_type = stream_args[0].canonical_name
            if stream_type in (StreamType.OUTPUT, StreamType.DUPLEX):
                idx = 1 if stream_type == StreamType.DUPLEX else 0
                event_output_type = stream_args[idx].canonical_name

            output_info = TypeInfo(
                name=stream_args[-1].canonical_name,
                module_path=stream_args[-1].canonical_path,
            )
        else:
            output_info = TypeInfo(name=output_type, module_path=returns.canonical_path)

        return OperationInfo(
            name=operation.name,
            module_path=operation.path,
            sync_module_path=sync_operation.path if sync_operation else None,
            input=input_info,
            input_dicts=input_dicts,
            async_only_input_dicts=async_only_input_dicts,
            output=output_info,
            stream_type=stream_type,
            event_input_type=event_input_type,
            event_output_type=event_output_type,
        )

    def _input_types(self, operation: Function) -> tuple[TypeInfo, list[TypeInfo]]:
        """Return an operation's input model and the dictionaries it accepts."""
        # Public request types live on the overloads; the implementation accepts
        # *args/**kwargs and does not expose the input shape.
        request_signature = next(
            (
                overload
                for overload in operation.overloads or []
                if "request" in overload.parameters
            ),
            None,
        )
        if request_signature:
            input_annotation = request_signature.parameters["request"].annotation
        else:
            input_annotation = operation.parameters["input"].annotation
        input_types = [
            TypeInfo(name=expr.canonical_name, module_path=expr.canonical_path)
            for expr in self._get_union_elements(
                self._get_expr(input_annotation, f"'{operation.name}' input annotation")
            )
        ]
        models = [t for t in input_types if not t.name.endswith("Dict")]
        if len(models) != 1:
            raise ValueError(f"'{operation.name}': expected one input model")
        return models[0], [t for t in input_types if t.name.endswith("Dict")]

    def _get_expr(self, annotation: str | Expr | None, context: str) -> Expr:
        """Extract and validate an Expr from an annotation."""
        if not isinstance(annotation, Expr):
            raise TypeError(
                f"{context}: expected Expr, got {type(annotation).__name__}"
            )
        return annotation

    def _get_subscript_elements(self, expr: Expr, context: str) -> list[Expr]:
        """Extract type arguments from a subscript expression like Generic[A, B, C]."""
        if not isinstance(expr, ExprSubscript):
            raise TypeError(f"{context}: expected subscript, got {type(expr).__name__}")
        slice_expr = expr.slice
        if isinstance(slice_expr, str):
            raise TypeError(f"{context}: unexpected string slice '{slice_expr}'")
        if isinstance(slice_expr, ExprTuple):
            return [el for el in slice_expr.elements if isinstance(el, Expr)]
        return [slice_expr]

    def _get_union_elements(self, expr: Expr) -> list[Expr]:
        """Flatten both Union[A, B] and A | B annotations."""
        if isinstance(expr, ExprBinOp) and expr.operator == "|":
            return [
                *self._get_union_elements(self._get_expr(expr.left, "Union member")),
                *self._get_union_elements(self._get_expr(expr.right, "Union member")),
            ]
        if (
            isinstance(expr, ExprSubscript)
            and isinstance(expr.left, Expr)
            and expr.left.canonical_name == "Union"
        ):
            return [
                member
                for arg in self._get_subscript_elements(expr, "Union")
                for member in self._get_union_elements(arg)
            ]
        return [expr]

    def _extract_models(
        self, models_module: Module, operations: list[OperationInfo]
    ) -> ModelsInfo:
        """Extract structures, unions, enums, and errors from models module."""
        structures, dictionaries, unions, enums, errors = [], [], [], [], []

        for member in models_module.members.values():
            if member.is_private:
                continue
            target = member
            if isinstance(member, Alias):
                # Partitioned clients re-export their types from private stubs.
                # Keep their public paths, while excluding unrelated imports.
                if not member.target_path.startswith(
                    f"{models_module.path.removesuffix('.models')}._private.models_"
                ):
                    continue
                target = member.final_target
            elif member.is_imported:
                continue

            if self._is_union(target):
                unions.append(
                    UnionInfo(
                        name=member.name,
                        module_path=member.path,
                        members=self._extract_union_members(target, models_module),
                    )
                )
            elif self._is_enum(target):
                enums.append(TypeInfo(name=member.name, module_path=member.path))
            elif self._is_error(target):
                errors.append(TypeInfo(name=member.name, module_path=member.path))
            elif isinstance(target, Class) and any(
                isinstance(base, Expr) and base.canonical_name == "TypedDict"
                for base in target.bases
            ):
                dictionaries.append(TypeInfo(name=member.name, module_path=member.path))
            elif target.is_class:
                structures.append(TypeInfo(name=member.name, module_path=member.path))

        def standalone(items: list[TypeInfo]) -> list[TypeInfo]:
            return [
                item
                for item in items
                if not self._is_operation_io_type(item.name, operations)
                and not self._is_union_member(item.name, unions)
            ]

        return ModelsInfo(
            structures=standalone(structures),
            dictionaries=standalone(dictionaries),
            unions=unions,
            enums=enums,
            errors=errors,
        )

    def _is_union(self, member: Object | Alias) -> TypeGuard[Attribute]:
        """Check if a module member is a union type."""
        if not isinstance(member, Attribute):
            return False

        value = member.value
        # Check for Union[...] syntax
        if isinstance(value, ExprSubscript):
            left = value.left
            if isinstance(left, ExprName) and left.name == "Union":
                return True

        # Check for PEP 604 (X | Y) syntax
        if isinstance(value, ExprBinOp) and value.operator == "|":
            return True

        return False

    def _extract_union_members(
        self, union_attr: Attribute, models_module: Module
    ) -> list[TypeInfo]:
        """Extract member types from a union."""
        members = []
        value = self._get_expr(union_attr.value, f"'{union_attr.name}' union")
        for expr in self._get_union_elements(value):
            name = expr.canonical_name
            if not (member_object := models_module.members.get(name)):
                raise ValueError(f"Union member '{name}' not found in models module")
            members.append(
                TypeInfo(name=member_object.name, module_path=member_object.path)
            )

        return members

    def _is_enum(self, member: Object | Alias) -> TypeGuard[Class]:
        """Check if a module member is an enum."""
        if not isinstance(member, Class):
            return False
        return any(
            isinstance(base, ExprName) and base.name in ENUM_BASE_CLASSES
            for base in member.bases
        )

    def _is_error(self, member: Object | Alias) -> TypeGuard[Class]:
        """Check if a module member is an error."""
        if not isinstance(member, Class):
            return False
        return any(
            isinstance(base, ExprName) and base.name in ERROR_BASE_CLASSES
            for base in member.bases
        )

    def _is_operation_io_type(
        self, type_name: str, operations: list[OperationInfo]
    ) -> bool:
        """Check if a type is used as operation input/output."""
        return any(
            type_name in (op.input.name, op.output.name)
            or any(type_name == dictionary.name for dictionary in op.input_dicts)
            for op in operations
        )

    def _is_union_member(self, type_name: str, unions: list[UnionInfo]) -> bool:
        """Check if a type is used as union member."""
        return any(type_name == m.name for u in unions for m in u.members)

    def _generate_client_docs(self, client_info: ClientInfo) -> bool:
        """Generate all documentation files for a client."""
        logger.info(f"Writing doc stubs to {self.output_dir}...")

        try:
            self._generate_index(client_info)
            self._generate_operation_stubs(client_info.operations)
            self._generate_type_stubs(
                client_info.models.structures, "structures", "Structure Class"
            )
            self._generate_type_stubs(
                client_info.models.dictionaries, "dictionaries", "Dictionary Type"
            )
            self._generate_type_stubs(
                client_info.models.errors, "errors", "Error Class"
            )
            self._generate_type_stubs(
                client_info.models.enums, "enums", "Enum Class", members=True
            )
            self._generate_union_stubs(client_info.models.unions)
        except OSError as e:
            logger.error(f"Failed to write documentation files: {e}")
            return False
        return True

    def _generate_index(self, client_info: ClientInfo) -> None:
        """Generate the main index.md file."""
        sync, async_ = client_info.sync, client_info.async_
        distribution = client_info.package_name.replace("_", "-")
        lines = [
            f"# {self.service_name}",
            "",
            "## Installation",
            "",
            f"To install the {self.service_name} client:",
            "",
            "```bash",
            f"python -m pip install {distribution}",
            "```",
            "",
            *self._bidirectional_streaming_setup(client_info, distribution),
            "## Client",
            "",
            f"The package provides a synchronous client, `{sync.client.name}`, and "
            f"an asynchronous client, `{async_.client.name}`. Both clients use "
            "the same models.",
            "",
        ]
        if any(op.sync_module_path is None for op in client_info.operations):
            lines.extend(
                [
                    "Operations that use event streams are available only on "
                    f"`{async_.client.name}`. They are marked **{ASYNC_ONLY_LABEL}** "
                    "under [Operations](#operations).",
                    "",
                ]
            )
        lines.extend(
            self._tabs(
                {mode.label: self._client_tab(mode) for mode in client_info.modes}
            )
        )

        # Operations section
        if client_info.operations:
            lines.append("## Operations")
            lines.append("")
            for op in sorted(client_info.operations, key=lambda x: x.name):
                badge = (
                    ""
                    if op.sync_module_path
                    else f' <span class="mode-badge">{ASYNC_ONLY_LABEL}</span>'
                )
                lines.append(f"- [`{op.name}`](operations/{op.name}.md){badge}")
            lines.append("")

        # Configuration section
        lines.extend(
            [
                "## Configuration",
                "",
                *self._tabs(
                    {mode.label: self._config_tab(mode) for mode in client_info.modes}
                ),
            ]
        )

        models = client_info.models

        # Model sections
        sections: list[tuple[str, str, Sequence[TypeInfo | UnionInfo]]] = [
            ("Structures", "structures", models.structures),
            ("Dictionaries", "dictionaries", models.dictionaries),
            ("Errors", "errors", models.errors),
            ("Unions", "unions", models.unions),
            ("Enums", "enums", models.enums),
        ]
        for title, folder, items in sections:
            if items:
                lines.append("")
                lines.append(f"## {title}")
                lines.append("")
                for item in sorted(items, key=lambda x: x.name):
                    lines.append(f"- [`{item.name}`]({folder}/{item.name}.md)")

        output_path = self.output_dir / "index.md"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        content = "\n".join(lines)
        output_path.write_text(content)

        logger.info("Wrote client index file")

    def _generate_operation_stubs(self, operations: list[OperationInfo]) -> None:
        """Generate operation documentation files."""
        for op in operations:
            lines = [f"# {op.name}", "", "## Operation", ""]
            if op.sync_module_path:
                lines.extend(
                    self._tabs(
                        {
                            SYNC_LABEL: self._mkdocs_directive(
                                op.sync_module_path, toc_label=SYNC_LABEL
                            ),
                            ASYNC_LABEL: self._mkdocs_directive(
                                op.module_path, toc_label=ASYNC_LABEL
                            ),
                        }
                    )
                )
            else:
                lines.extend(
                    [
                        f'!!! info "{ASYNC_ONLY_LABEL}"',
                        "",
                        "    This operation uses an event stream, so only the "
                        "asynchronous client supports it.",
                        "",
                        *self._mkdocs_directive(op.module_path, toc_label=ASYNC_LABEL),
                        "",
                    ]
                )
            lines.extend(["## Input", ""])
            if op.input_dicts:
                lines.extend(
                    [
                        "Pass the input as keyword arguments, a positional dictionary, or a "
                        "positional model object. Pass `plugins` separately as a keyword argument.",
                        "",
                    ]
                )
                # The dictionaries and the model have the same fields, so show one
                # at a time. Dictionaries come first: keyword arguments, the most
                # common way to call an operation, follow their fields.
                dictionaries = self._async_only_dicts_note(op)
                for dictionary in op.input_dicts:
                    if dictionaries:
                        dictionaries.append("")
                    dictionaries.extend(self._mkdocs_directive(dictionary.module_path))
                lines.extend(
                    self._tabs(
                        {
                            DICTIONARY_LABEL: dictionaries,
                            MODEL_LABEL: self._mkdocs_directive(op.input.module_path),
                        }
                    )
                )
            else:
                lines.extend(self._mkdocs_directive(op.input.module_path))
            lines.extend(["", "## Output", ""])

            if op.stream_type:
                lines.extend(
                    [
                        f"This operation returns {op.stream_type.description}.",
                        "",
                        "### Event Stream Structure",
                        "",
                    ]
                )

                if op.event_input_type:
                    lines.extend(
                        [
                            "#### Input Event Type",
                            "",
                            f"[`{op.event_input_type}`](../unions/{op.event_input_type}.md)",
                            "",
                        ]
                    )
                if op.event_output_type:
                    lines.extend(
                        [
                            "#### Output Event Type",
                            "",
                            f"[`{op.event_output_type}`](../unions/{op.event_output_type}.md)",
                            "",
                        ]
                    )

                lines.extend(
                    [
                        "### Initial Response Structure",
                        "",
                        *self._mkdocs_directive(op.output.module_path, heading_level=4),
                    ]
                )
            else:
                lines.extend(self._mkdocs_directive(op.output.module_path))

            output_path = self.output_dir / "operations" / f"{op.name}.md"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(self._breadcrumb("Operations") + "\n".join(lines))

        logger.info(f"Wrote {len(operations)} operation file(s)")

    def _generate_type_stubs(
        self,
        items: list[TypeInfo],
        category: str,
        section_title: str,
        members: bool | None = None,
    ) -> None:
        """Generate documentation files for a category of types."""
        for item in items:
            lines = [
                f"# {item.name}",
                "",
                f"## {section_title}",
                *self._mkdocs_directive(item.module_path, members=members),
            ]

            output_path = self.output_dir / category / f"{item.name}.md"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                self._breadcrumb(category.title()) + "\n".join(lines)
            )

        logger.info(f"Wrote {len(items)} {category} file(s)")

    def _generate_union_stubs(self, unions: list[UnionInfo]) -> None:
        """Generate union documentation files."""
        for union in unions:
            lines = [
                f"# {union.name}",
                "",
                "## Union Type",
                *self._mkdocs_directive(union.module_path),
                "",
            ]

            # Add union members
            if union.members:
                lines.append("## Union Member Types")
                for member in union.members:
                    lines.append("")
                    lines.extend(self._mkdocs_directive(member.module_path))

            output_path = self.output_dir / "unions" / f"{union.name}.md"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(self._breadcrumb("Unions") + "\n".join(lines))

        logger.info(f"Wrote {len(unions)} union file(s)")

    def _bidirectional_streaming_setup(
        self, client_info: ClientInfo, distribution: str
    ) -> list[str]:
        """Generate the CRT install step, for clients with bidirectional streams."""
        if not any(
            op.stream_type is StreamType.DUPLEX for op in client_info.operations
        ):
            return []
        pyproject = tomllib.loads(
            (self.client_dir.parent.parent / "pyproject.toml").read_text()
        )
        if CRT_EXTRA not in pyproject["project"].get("optional-dependencies", {}):
            raise ValueError(
                f"{distribution} has bidirectional streams but no '{CRT_EXTRA}' extra"
            )
        return [
            "### Bidirectional streaming",
            "",
            "This client supports bidirectional event streams, which require the AWS CRT "
            f"HTTP client. To use this feature, install the package with the `{CRT_EXTRA}` extra:",
            "",
            "```bash",
            f'python -m pip install "{distribution}[{CRT_EXTRA}]"',
            "```",
            "",
            "Then pass an `AWSCRTHTTPClient` instance as the transport when you resolve the "
            "config.",
            "",
        ]

    def _client_tab(self, mode: ClientModeInfo) -> list[str]:
        """Generate a mode's Client tab: the client class and non-operation methods."""
        lines = self._mkdocs_directive(
            mode.client.module_path,
            members=False,
            merge_init_into_class=True,
            ignore_init_summary=True,
        )
        for method in sorted(mode.client_methods, key=lambda x: x.name):
            lines.extend(
                ["", *self._mkdocs_directive(method.module_path, heading_level=4)]
            )
        return lines

    def _config_tab(self, mode: ClientModeInfo) -> list[str]:
        """Generate a mode's Configuration tab: the config and Plugin types."""
        return [
            # No constructor signature: configs are built with resolve(), and
            # calling the class directly raises.
            *self._mkdocs_directive(mode.config.module_path),
            "",
            # Both modes define a Plugin, so the table of contents label tells
            # them apart.
            *self._mkdocs_directive(
                mode.plugin.module_path,
                toc_label=f"{mode.plugin.name} ({mode.label})",
            ),
        ]

    def _async_only_dicts_note(self, op: OperationInfo) -> list[str]:
        """Generate a note naming input dictionaries only the async client accepts."""
        if not (op.sync_module_path and op.async_only_input_dicts):
            return []

        def names(dicts: list[TypeInfo]) -> str:
            return ", ".join(f"`{d.name}`" for d in dicts)

        shared = [d for d in op.input_dicts if d not in op.async_only_input_dicts]
        note = (
            f"Only the asynchronous client accepts {names(op.async_only_input_dicts)}."
        )
        if shared:
            note = f"Both clients accept {names(shared)}. {note}"
        return [note]

    def _tabs(self, tabs: dict[str, list[str]]) -> list[str]:
        """Wrap each label's lines in a content tab, ending with a blank line."""
        lines = []
        for label, body in tabs.items():
            lines.extend([f'=== "{label}"', ""])
            lines.extend(f"    {line}" if line else "" for line in body)
            lines.append("")
        return lines

    def _mkdocs_directive(
        self,
        module_path: str,
        heading_level: int = 3,
        members: bool | None = None,
        merge_init_into_class: bool = False,
        ignore_init_summary: bool = False,
        toc_label: str | None = None,
    ) -> list[str]:
        """Generate mkdocstrings directive lines for a module path.

        Args:
            module_path: The Python module path for the directive.
            heading_level: The heading level for rendered documentation.
            members: Whether to show members (None omits the option).
            merge_init_into_class: Whether to merge __init__ docstring into class docs.
            ignore_init_summary: Whether to ignore init summary in docstrings.
            toc_label: The object's label in the page's table of contents
                (None uses its name).

        Returns:
            List of strings representing the mkdocstrings directive.
        """
        lines = [
            f"::: {module_path}",
            "    options:",
            f"        heading_level: {heading_level}",
        ]
        if members is not None:
            lines.append(f"        members: {'true' if members else 'false'}")
        if merge_init_into_class:
            lines.append("        merge_init_into_class: true")
        if toc_label:
            lines.append(f'        toc_label: "{toc_label}"')
        if ignore_init_summary:
            lines.append("        docstring_options:")
            lines.append("            ignore_init_summary: true")

        return lines

    def _breadcrumb(self, category: str) -> str:
        """Generate a breadcrumb trail in the theme's navigation path markup.

        Symbol pages are left out of the navigation to keep the sidebar small, so
        the theme renders no path for them. Like its path, this lists ancestors only.
        """
        items = "\n".join(
            f'<li class="md-path__item" markdown>[<span class="md-ellipsis">{title}</span>]'
            f"({href}){{ .md-path__link }}</li>"
            for title, href in [
                (self.service_name, "../index.md"),
                (category, f"../index.md#{category.lower()}"),
            ]
        )
        return (
            '<nav class="md-path" aria-label="Navigation" markdown>\n'
            f'<ol class="md-path__list" markdown>\n{items}\n</ol>\n</nav>\n\n'
        )


def main() -> int:
    """Main entry point for the single-client documentation generator."""
    parser = argparse.ArgumentParser(
        description="Generate API documentation stubs for AWS SDK Python client."
    )
    parser.add_argument(
        "-c",
        "--client-dir",
        type=Path,
        required=True,
        help="Path to the client source package",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        required=True,
        help="Output directory for generated doc stubs",
    )
    parser.add_argument(
        "-s",
        "--service-name",
        default=None,
        help="Display name for the service (Smithy sdkId, e.g. 'SNS')",
    )

    args = parser.parse_args()
    client_dir = args.client_dir.resolve()
    output_dir = args.output_dir.resolve()

    if not client_dir.exists():
        logger.error(f"Client directory not found: {client_dir}")
        return 1

    try:
        generator = DocStubGenerator(client_dir, output_dir, args.service_name)
        success = generator.generate()
        return 0 if success else 1
    except Exception as e:
        logger.error(f"Unexpected error generating doc stubs: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
