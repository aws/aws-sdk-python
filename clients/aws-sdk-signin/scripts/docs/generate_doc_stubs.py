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


class StreamType(Enum):
    """Type of event stream for operations."""

    INPUT = "InputEventStream"
    OUTPUT = "OutputEventStream"
    DUPLEX = "DuplexEventStream"

    @property
    def description(self) -> str:
        """Return a string description for documentation."""
        descriptions = {
            StreamType.INPUT: "an `InputEventStream` for client-to-server streaming",
            StreamType.OUTPUT: "an `OutputEventStream` for server-to-client streaming",
            StreamType.DUPLEX: "a `DuplexEventStream` for bidirectional streaming",
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
    module_path: str
    input: TypeInfo
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
    unions: list[UnionInfo]
    enums: list[TypeInfo]
    errors: list[TypeInfo]


@dataclass
class ClientInfo:
    """Complete information about a client package."""

    name: str  # e.g., "BedrockRuntimeClient"
    module_path: str  # e.g., "aws_sdk_bedrock_runtime.client.BedrockRuntimeClient"
    package_name: str  # e.g., "aws_sdk_bedrock_runtime"
    config: TypeInfo
    plugin: TypeInfo
    client_methods: list[ClientMethodInfo]
    operations: list[OperationInfo]
    models: ModelsInfo


class DocStubGenerator:
    """Generate markdown API Reference stubs for AWS SDK for Python v4 clients."""

    def __init__(self, client_dir: Path, output_dir: Path, service_name: str | None = None) -> None:
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

        The generated ``_private/schemas.py`` carries the ``aws.api#service``
        trait's ``sdkId`` (e.g. "SNS"), the same field the sidebar navigation
        uses, so it keeps acronym casing that the package name does not.
        Returns None if the file or value is absent.
        """
        schemas = client_dir / "_private" / "schemas.py"
        if not schemas.is_file():
            return None
        match = re.search(r'"sdkId":\s*"([^"]+)"', schemas.read_text())
        return match.group(1) if match else None

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
        package = griffe.load(package_name)

        # Ensure required modules exist
        required = ("client", "config", "models")
        missing = [name for name in required if not package.modules.get(name)]
        if missing:
            raise ValueError(f"Missing required modules in {package_name}: {', '.join(missing)}")

        # Parse submodules
        client_module = package.modules["client"]
        config_module = package.modules["config"]
        models_module = package.modules["models"]

        client_class = self._find_class_with_suffix(client_module, "Client")
        if not client_class:
            raise ValueError(f"No class ending with 'Client' found in {package_name}.client")

        config_class = self._find_class_with_suffix(config_module, "Config")
        if not config_class:
            raise ValueError(f"No class ending with 'Config' found in {package_name}.config")

        plugin_alias = config_module.members.get("Plugin")
        if not plugin_alias:
            raise ValueError(f"Missing Plugin in {package_name}.config")

        config = TypeInfo(name=config_class.name, module_path=config_class.path)
        plugin = TypeInfo(name=plugin_alias.name, module_path=plugin_alias.path)

        client_methods = self._extract_client_methods(client_class)
        operations = self._extract_operations(client_class)
        models = self._extract_models(models_module, operations)

        logger.info(
            f"Analyzed {client_class.name}: {len(client_methods)} client methods, "
            f"{len(operations)} operations, "
            f"{len(models.structures)} structures, {len(models.errors)} errors, "
            f"{len(models.unions)} unions, {len(models.enums)} enums"
        )

        return ClientInfo(
            name=client_class.name,
            module_path=client_class.path,
            package_name=package_name,
            config=config,
            plugin=plugin,
            client_methods=client_methods,
            operations=operations,
            models=models,
        )

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

    def _extract_operations(self, client_class: Class) -> list[OperationInfo]:
        """Extract operation information from client class."""
        operations = []
        for op in client_class.functions.values():
            if (
                op.is_private
                or op.is_init_method
                or op.is_special
                or op.name in CLIENT_METHOD_NAMES
            ):
                continue
            operations.append(self._analyze_operation(op))
        return operations

    def _extract_client_methods(self, client_class: Class) -> list[ClientMethodInfo]:
        """Extract public client methods that are not service operations."""
        return [
            ClientMethodInfo(name=method.name, module_path=method.path)
            for method in client_class.functions.values()
            if not method.is_private and method.name in CLIENT_METHOD_NAMES
        ]

    def _analyze_operation(self, operation: Function) -> OperationInfo:
        """Analyze an operation method to extract information."""
        stream_type = None
        event_input_type = None
        event_output_type = None

        input_param = operation.parameters["input"]
        input_annotation = self._get_expr(
            input_param.annotation, f"'{operation.name}' input annotation"
        )
        input_info = TypeInfo(
            name=input_annotation.canonical_name,
            module_path=input_annotation.canonical_path,
        )

        returns = self._get_expr(operation.returns, f"'{operation.name}' return type")
        output_type = returns.canonical_name
        stream_type_map = {s.value: s for s in StreamType}

        if output_type in stream_type_map:
            stream_type = stream_type_map[output_type]
            stream_args = self._get_subscript_elements(returns, f"'{operation.name}' stream type")

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
            input=input_info,
            output=output_info,
            stream_type=stream_type,
            event_input_type=event_input_type,
            event_output_type=event_output_type,
        )

    def _get_expr(self, annotation: str | Expr | None, context: str) -> Expr:
        """Extract and validate an Expr from an annotation."""
        if not isinstance(annotation, Expr):
            raise TypeError(f"{context}: expected Expr, got {type(annotation).__name__}")
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

    def _extract_models(self, models_module: Module, operations: list[OperationInfo]) -> ModelsInfo:
        """Extract structures, unions, enums, and errors from models module."""
        structures, unions, enums, errors = [], [], [], []

        for member in models_module.members.values():
            # Skip imported and private members
            if member.is_imported or member.is_private:
                continue

            if self._is_union(member):
                unions.append(
                    UnionInfo(
                        name=member.name,
                        module_path=member.path,
                        members=self._extract_union_members(member, models_module),
                    )
                )
            elif self._is_enum(member):
                enums.append(TypeInfo(name=member.name, module_path=member.path))
            elif self._is_error(member):
                errors.append(TypeInfo(name=member.name, module_path=member.path))
            elif member.is_class:
                structures.append(TypeInfo(name=member.name, module_path=member.path))

        duplicates = []
        for structure in structures:
            if self._is_operation_io_type(structure.name, operations) or self._is_union_member(
                structure.name, unions
            ):
                duplicates.append(structure)

        structures = [struct for struct in structures if struct not in duplicates]

        return ModelsInfo(structures=structures, unions=unions, enums=enums, errors=errors)

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
        if isinstance(value, ExprBinOp):
            return True

        return False

    def _extract_union_members(
        self, union_attr: Attribute, models_module: Module
    ) -> list[TypeInfo]:
        """Extract member types from a union."""
        members = []
        value_str = str(union_attr.value)

        # Clean up value_str for Union[X | Y | Z] syntax
        if value_str.startswith("Union[") and value_str.endswith("]"):
            value_str = value_str.removeprefix("Union[").removesuffix("]")

        member_names = [member.strip() for member in value_str.split("|")]

        for name in member_names:
            if not (member_object := models_module.members.get(name)):
                raise ValueError(f"Union member '{name}' not found in models module")
            members.append(TypeInfo(name=member_object.name, module_path=member_object.path))

        return members

    def _is_enum(self, member: Object | Alias) -> TypeGuard[Class]:
        """Check if a module member is an enum."""
        if not isinstance(member, Class):
            return False
        return any(
            isinstance(base, ExprName) and base.name in ENUM_BASE_CLASSES for base in member.bases
        )

    def _is_error(self, member: Object | Alias) -> TypeGuard[Class]:
        """Check if a module member is an error."""
        if not isinstance(member, Class):
            return False
        return any(
            isinstance(base, ExprName) and base.name in ERROR_BASE_CLASSES for base in member.bases
        )

    def _is_operation_io_type(self, type_name: str, operations: list[OperationInfo]) -> bool:
        """Check if a type is used as operation input/output."""
        return any(type_name in (op.input.name, op.output.name) for op in operations)

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
            self._generate_type_stubs(client_info.models.errors, "errors", "Error Class")
            self._generate_type_stubs(client_info.models.enums, "enums", "Enum Class", members=True)
            self._generate_union_stubs(client_info.models.unions)
        except OSError as e:
            logger.error(f"Failed to write documentation files: {e}")
            return False
        return True

    def _generate_index(self, client_info: ClientInfo) -> None:
        """Generate the main index.md file."""
        lines = [
            f"# {self.service_name}",
            "",
            "## Installation",
            "",
            f"To install the {self.service_name} client:",
            "",
            "```bash",
            f"python -m pip install {client_info.package_name.replace('_', '-')}",
            "```",
            "",
            "## Client",
            "",
            *self._mkdocs_directive(
                client_info.module_path,
                members=False,
                merge_init_into_class=True,
                ignore_init_summary=True,
            ),
            "",
        ]

        for method in sorted(client_info.client_methods, key=lambda x: x.name):
            lines.extend([*self._mkdocs_directive(method.module_path, heading_level=4), ""])

        # Operations section
        if client_info.operations:
            lines.append("## Operations")
            lines.append("")
            for op in sorted(client_info.operations, key=lambda x: x.name):
                lines.append(f"- [`{op.name}`](operations/{op.name}.md)")
            lines.append("")

        # Configuration section
        lines.extend(
            [
                "## Configuration",
                "",
                *self._mkdocs_directive(
                    client_info.config.module_path,
                    merge_init_into_class=True,
                    ignore_init_summary=True,
                ),
                "",
                *self._mkdocs_directive(client_info.plugin.module_path),
            ]
        )

        models = client_info.models

        # Model sections
        sections: list[tuple[str, str, Sequence[TypeInfo | UnionInfo]]] = [
            ("Structures", "structures", models.structures),
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
            lines = [
                f"# {op.name}",
                "",
                "## Operation",
                "",
                *self._mkdocs_directive(op.module_path),
                "",
                "## Input",
                "",
                *self._mkdocs_directive(op.input.module_path),
                "",
                "## Output",
                "",
            ]

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
            output_path.write_text(self._breadcrumb("Operations", op.name) + "\n".join(lines))

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
            output_path.write_text(self._breadcrumb(category.title(), item.name) + "\n".join(lines))

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
            output_path.write_text(self._breadcrumb("Unions", union.name) + "\n".join(lines))

        logger.info(f"Wrote {len(unions)} union file(s)")

    def _mkdocs_directive(
        self,
        module_path: str,
        heading_level: int = 3,
        members: bool | None = None,
        merge_init_into_class: bool = False,
        ignore_init_summary: bool = False,
    ) -> list[str]:
        """Generate mkdocstrings directive lines for a module path.

        Args:
            module_path: The Python module path for the directive.
            heading_level: The heading level for rendered documentation.
            members: Whether to show members (None omits the option).
            merge_init_into_class: Whether to merge __init__ docstring into class docs.
            ignore_init_summary: Whether to ignore init summary in docstrings.

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
        if ignore_init_summary:
            lines.append("        docstring_options:")
            lines.append("            ignore_init_summary: true")

        return lines

    def _breadcrumb(self, category: str, name: str) -> str:
        """Generate a breadcrumb navigation element."""
        separator = "&nbsp;&nbsp;>&nbsp;&nbsp;"
        home = f"[{self.service_name}](../index.md)"
        section = f"[{category}](../index.md#{category.lower()})"
        return f'<span class="breadcrumb">{home}{separator}{section}{separator}{name}</span>\n'


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
