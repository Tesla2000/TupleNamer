from __future__ import annotations

from importlib import import_module
from pathlib import Path

from .main import main
from .str_consts.src.tuple_namer import EMPTY
from .str_consts.src.tuple_namer import INIT_PY
from .str_consts.src.tuple_namer import PY
from .str_consts.src.tuple_namer import PYCACHE

_ = main


def import_python(root: Path):
    for module_path in root.glob(PY):
        if module_path.name in (INIT_PY, PYCACHE, "__pycache__"):
            continue
        if module_path.is_file():
            relative_path = module_path.relative_to(Path(__file__).parent)
            subfolders = EMPTY.join(
                map(".{}".format, relative_path.parts[:-1])
            )
            str_path = module_path.with_suffix(EMPTY).name
            import_module("." + str_path, __name__ + subfolders)
            yield module_path.with_suffix(EMPTY).name
            continue
        yield from import_python(module_path)


__all__ = ["main"] + list(import_python(Path(__file__).parent))
