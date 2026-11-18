"""Adapt generated clients and their operations for the API reference."""

import ast
from typing import Any

from griffe import (
    Class,
    Docstring,
    ExprBinOp,
    ExprSubscript,
    Extension,
    Function,
    Parameter,
    ParameterKind,
    Parameters,
    get_expression,
)

# Generated clients subclass these and inherit their constructor.
CLIENT_BASES = ("smithy_core.client.Client", "smithy_core.aio.client.AsyncClient")


class OverloadDocstrings(Extension):
    """Use an overload's docstring when the implementation has none."""

    def on_function(self, *, func: Function, **kwargs: Any) -> None:
        if func.docstring:
            return
        for overload in func.overloads or []:
            if docstring := overload.docstring:
                func.docstring = Docstring(
                    docstring.value,
                    lineno=docstring.lineno,
                    endlineno=docstring.endlineno,
                    parent=func,
                    parser=docstring.parser,
                    parser_options=docstring.parser_options,
                )
                break


class MergedOperationSignature(Extension):
    """Show each operation with one signature covering every way to pass input.

    Generated operations have two overloads: the request (a model or dictionary)
    passed positionally, and its fields as keyword arguments. Rendering both looks
    like a duplicate and neither covers every form, so this merges them and
    documents ``request`` and ``**kwargs`` alongside ``plugins``.
    """

    def on_function(self, *, func: Function, **kwargs: Any) -> None:
        overloads = func.overloads or []
        request = [o for o in overloads if "request" in o.parameters]
        keyword = [
            o
            for o in overloads
            if any(p.kind is ParameterKind.var_keyword for p in o.parameters)
        ]
        if len(overloads) != 2 or len(request) != 1 or len(keyword) != 1:
            return
        [request_overload], [keyword_overload] = request, keyword
        request_annotation = request_overload.parameters["request"].annotation
        if request_overload is keyword_overload or request_annotation is None:
            return

        parameters = list(keyword_overload.parameters)
        parameters.insert(
            1 if parameters and parameters[0].name == "self" else 0,
            Parameter(
                "request",
                annotation=ExprBinOp(request_annotation, "|", "None"),
                kind=ParameterKind.positional_only,
                default="None",
            ),
        )
        func.parameters = Parameters(*parameters)
        func.returns = keyword_overload.returns
        func.overloads = None

        if docstring := func.docstring:
            func.docstring = Docstring(
                _document_input_arguments(docstring.value),
                lineno=docstring.lineno,
                endlineno=docstring.endlineno,
                parent=func,
                parser=docstring.parser,
                parser_options=docstring.parser_options,
            )


def _document_input_arguments(docstring: str) -> str:
    """Document ``request`` first and ``**kwargs`` last in the Args section.

    A docstring without an Args section gets one before its Returns section.
    """
    request_entry = [
        "    request:",
        "        The input as a model or dictionary. Pass this or keyword",
        "        arguments, not both.",
    ]
    kwargs_entry = ["    **kwargs:", "        The input fields as keyword arguments."]
    lines = docstring.splitlines()
    if "Args:" not in lines:
        at = lines.index("Returns:") if "Returns:" in lines else len(lines)
        section = ["Args:", *request_entry, *kwargs_entry, ""]
        return "\n".join([*lines[:at], *section, *lines[at:]])

    # The section's entries are indented, so it ends at the next unindented
    # line. Blank lines before that line stay after the new last entry.
    start = lines.index("Args:") + 1
    end = next(
        (i for i in range(start, len(lines)) if lines[i] and not lines[i][0].isspace()),
        len(lines),
    )
    while end > start and not lines[end - 1].strip():
        end -= 1
    return "\n".join(
        [*lines[:start], *request_entry, *lines[start:end], *kwargs_entry, *lines[end:]]
    )


class ClientConstructors(Extension):
    """Give generated clients the constructor signature they inherit.

    Clients inherit a generic ``__init__(config, plugins)`` from smithy-core,
    which the API reference doesn't load, so this adds one typed with the
    client's own config and ``Plugin``.
    """

    def on_class_members(self, *, cls: Class, **kwargs: Any) -> None:
        if "__init__" in cls.members or "Plugin" not in cls.module.members:
            return
        base = next(
            (
                base
                for base in cls.bases
                if isinstance(base, ExprSubscript)
                and getattr(base.left, "canonical_path", None) in CLIENT_BASES
            ),
            None,
        )
        if base is None:
            return

        def annotation(source: str) -> Any:
            return get_expression(ast.parse(source, mode="eval").body, parent=cls)

        cls.set_member(
            "__init__",
            Function(
                "__init__",
                lineno=cls.lineno,
                endlineno=cls.lineno,
                parameters=Parameters(
                    Parameter("self", kind=ParameterKind.positional_or_keyword),
                    Parameter(
                        "config",
                        annotation=annotation(f"{base.slice} | None"),
                        kind=ParameterKind.positional_or_keyword,
                        default="None",
                    ),
                    Parameter(
                        "plugins",
                        annotation=annotation("list[Plugin] | None"),
                        kind=ParameterKind.positional_or_keyword,
                        default="None",
                    ),
                ),
                returns="None",
            ),
        )
