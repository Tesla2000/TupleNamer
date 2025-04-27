from __future__ import annotations

import json
from typing import TypeVar

import inflect
import libcst
import libcst as cst
from libcst import Annotation
from libcst import Arg
from libcst import Call
from libcst import CSTNode
from libcst import Ellipsis as LibcstEllipsis
from libcst import FunctionDef
from libcst import Import
from libcst import ImportAlias
from libcst import ImportFrom
from libcst import Module
from libcst import Name
from libcst import Return
from libcst import SimpleStatementLine
from libcst import Subscript
from libcst import SubscriptElement
from libcst import Tuple
from litellm import completion
from more_itertools import last
from pydantic import create_model

from ..config import Config
from ..str_consts.src.tuple_namer import EMPTY
from ..str_consts.src.tuple_namer import STAR
from ..str_consts.src.tuple_namer import UNDERSCORE
from ..str_consts.src.tuple_namer.transform.transformer import ARGUMENT
from ..str_consts.src.tuple_namer.transform.transformer import CONTENT
from ..str_consts.src.tuple_namer.transform.transformer import GPT_4O_MINI
from ..str_consts.src.tuple_namer.transform.transformer import MESSAGE
from ..str_consts.src.tuple_namer.transform.transformer import NAMED_TUPLE
from ..str_consts.src.tuple_namer.transform.transformer import (
    NAMED_TUPLE_FIELDS,
)
from ..str_consts.src.tuple_namer.transform.transformer import NT_FORMATTED
from ..str_consts.src.tuple_namer.transform.transformer import ROLE
from ..str_consts.src.tuple_namer.transform.transformer import TUPLE
from ..str_consts.src.tuple_namer.transform.transformer import TUPLE_NAME
from ..str_consts.src.tuple_namer.transform.transformer import TYPING
from ..str_consts.src.tuple_namer.transform.transformer import (
    TYPING_EXTENSIONS,
)
from ..str_consts.src.tuple_namer.transform.transformer import USER

T = TypeVar("T", bound=CSTNode)

p = inflect.engine()


class Transformer(cst.CSTTransformer):
    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.modified_returns = {}

    def leave_FunctionDef(
        self, original_node: "FunctionDef", updated_node: "FunctionDef"
    ) -> "FunctionDef":
        if updated_node.returns is None:
            return updated_node
        annotation = updated_node.returns.annotation
        if not (
            isinstance(annotation, Subscript)
            and isinstance(value := annotation.value, Name)
            and value.value == TUPLE
            and (
                len(slice := annotation.slice) < 2
                or not isinstance(slice[1].slice.value, LibcstEllipsis)
            )
        ):
            return updated_node
        types = tuple(map(self._get_slice_value, slice))
        arg_names = tuple(
            p.number_to_words(p.ordinal(num), comma=EMPTY, andword=EMPTY)
            .replace(",", EMPTY)
            .replace("-", EMPTY)
            + ARGUMENT
            for num in range(len(types))
        )
        model = create_model(
            NAMED_TUPLE_FIELDS,
            tuple_name=str,
            **{name: str for name in arg_names},
        )
        response = json.loads(
            completion(
                GPT_4O_MINI,
                messages=[
                    {
                        ROLE: USER,
                        CONTENT: (
                            "Peak suitable field names for the namedtuple fields and the name of the namedtuple that is a return value of the function bellow. Note field names must be single word or words connected with _:\n"
                            + Module([original_node]).code
                        ),
                    }
                ],
                temperature=0.0,
                response_format=model,
            ).choices[0][MESSAGE][CONTENT]
        )
        tuple_name = UNDERSCORE + response.pop(TUPLE_NAME).lstrip(UNDERSCORE)
        updated_node = updated_node.with_changes(
            returns=Annotation(annotation=Name(tuple_name))
        )
        updated_node = updated_node.visit(_ReturnReplacer(tuple_name))
        self.modified_returns[updated_node] = (
            f"class {tuple_name}(NamedTuple):"
            + EMPTY.join(
                NT_FORMATTED.format(value, type_hint)
                for value, type_hint in zip(response.values(), types)
            )
        )
        return updated_node

    def leave_Module(
        self, original_node: "Module", updated_node: "Module"
    ) -> "Module":
        body = list(updated_node.body)
        if self.modified_returns and not any(
            map(
                lambda elem: isinstance(elem, SimpleStatementLine)
                and isinstance(import_ := elem.body[0], ImportFrom)
                and import_.module.value in (TYPING, TYPING_EXTENSIONS)
                and any(
                    alias.name.value == NAMED_TUPLE for alias in import_.names
                ),
                body,
            )
        ):
            body.insert(
                0,
                SimpleStatementLine(
                    [
                        ImportFrom(
                            Name(TYPING), [ImportAlias(Name(NAMED_TUPLE))]
                        )
                    ]
                ),
            )
        updated_node = updated_node.with_changes(body=tuple(body))
        return self._add_named_tuples(original_node, updated_node)

    def _add_named_tuples(self, _: T, updated_node: T) -> T:
        if self.modified_returns:
            body = list(updated_node.body)
            for func in filter(
                dict(self.modified_returns).get, updated_node.body
            ):
                body.insert(
                    body.index(func),
                    libcst.parse_statement(self.modified_returns.pop(func)),
                )
            import_index = (
                body.index(
                    last(
                        filter(
                            lambda elem: isinstance(elem, SimpleStatementLine)
                            and isinstance(elem.body[0], (ImportFrom, Import)),
                            body,
                        )
                    )
                )
                + 1
            )
            for value in self.modified_returns.values():
                body.insert(import_index, libcst.parse_statement(value))
            return updated_node.with_changes(body=tuple(body))
        return updated_node

    @staticmethod
    def _get_slice_value(subscript_element: SubscriptElement) -> str:
        return Module([subscript_element.slice]).code


class _ReturnReplacer(cst.CSTTransformer):
    def __init__(self, class_name: str):
        super().__init__()
        self.class_name = class_name

    def leave_Return(
        self, original_node: "Return", updated_node: "Return"
    ) -> "Return":
        return updated_node.with_changes(
            value=Call(
                Name(self.class_name),
                [
                    Arg(
                        updated_node.value,
                        star=STAR
                        * (
                            bool(updated_node.value.lpar)
                            or not isinstance(updated_node.value, Tuple)
                        ),
                    )
                ],
            )
        )


class Visitor(cst.CSTVisitor):
    def __init__(self, config: Config):
        super().__init__()
        self.config = config
