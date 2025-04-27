from __future__ import annotations

import argparse
from types import GenericAlias
from typing import Any

from .str_consts.src.tuple_namer import STAR
from .str_consts.src.tuple_namer.custom_argument_parser import FALSE
from .str_consts.src.tuple_namer.custom_argument_parser import N
from .str_consts.src.tuple_namer.custom_argument_parser import NARGS
from .str_consts.src.tuple_namer.custom_argument_parser import NO
from .str_consts.src.tuple_namer.custom_argument_parser import T
from .str_consts.src.tuple_namer.custom_argument_parser import TRUE
from .str_consts.src.tuple_namer.custom_argument_parser import TYPE
from .str_consts.src.tuple_namer.custom_argument_parser import Y
from .str_consts.src.tuple_namer.custom_argument_parser import YES


class CustomArgumentParser(argparse.ArgumentParser):
    def add_argument(
        self,
        *args,
        **kwargs,
    ):
        if isinstance(kwargs.get(TYPE), GenericAlias):
            kwargs[TYPE] = kwargs.get(TYPE).__origin__
        if isinstance(kwargs.get(TYPE), type):
            if issubclass(kwargs.get(TYPE), bool):
                kwargs[TYPE] = self._str2bool
            elif issubclass(kwargs.get(TYPE), list):
                kwargs[NARGS] = STAR
                kwargs[TYPE] = str
            elif issubclass(kwargs.get(TYPE), tuple):
                kwargs[NARGS] = "+"
                kwargs[TYPE] = str
        super().add_argument(
            *args,
            **kwargs,
        )

    def _str2bool(self, v: Any) -> Any:
        if isinstance(v, bool):
            return v
        if v.lower() in (YES, TRUE, T, Y, "1"):
            return True
        elif v.lower() in (NO, FALSE, "f", N, "0"):
            return False
        else:
            raise argparse.ArgumentTypeError(
                f"Boolean value expected got {v}."
            )
