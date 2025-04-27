from __future__ import annotations

from collections.abc import Iterable
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def transation(pos_args: Iterable[str]):
    paths = tuple(map(Path, pos_args))
    contents = tuple(path.read_text() for path in paths)
    try:
        yield
    except BaseException:
        print("Reverting changes please wait until process is done...")
        for path, content in zip(paths, contents):
            path.write_text(content)
        print("Changes reverted")
        raise
