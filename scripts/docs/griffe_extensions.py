"""Preserve operation descriptions stored on generated overloads."""

from typing import Any

from griffe import Docstring, Extension, Function


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
