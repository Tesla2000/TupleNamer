from __future__ import annotations

from pathlib import Path
from typing import get_origin
from typing import Literal
from typing import Optional
from typing import Type

import toml
from pydantic import BaseModel
from pydantic import Field
from pydantic_core import PydanticUndefined

from .custom_argument_parser import CustomArgumentParser
from .str_consts.src.tuple_namer import EMPTY
from .str_consts.src.tuple_namer import UNDERSCORE
from .str_consts.src.tuple_namer.config import ARGS
from .str_consts.src.tuple_namer.config import CONFIG_FILE
from .str_consts.src.tuple_namer.config import DEFAULT_FORMATTED
from .str_consts.src.tuple_namer.config import ENV
from .str_consts.src.tuple_namer.config import FORMATTED
from .str_consts.src.tuple_namer.config import POS_ARGS


class Config(BaseModel):
    _root: Path = Path(__file__).parent
    pos_args: list[str] = Field(default_factory=list)
    config_file: Optional[Path] = None
    env_file_path: Path = Path(ENV)


def parse_arguments(config_class: Type[Config]):
    parser = CustomArgumentParser(
        description="Configure the application settings."
    )

    for name, value in config_class.model_fields.items():
        if name.startswith(UNDERSCORE):
            continue
        annotation = value.annotation
        if len(getattr(value.annotation, ARGS, [])) > 1:
            annotation = next(filter(None, value.annotation.__args__))
        if get_origin(value.annotation) == Literal:
            annotation = str
        parser.add_argument(
            FORMATTED.format(name) if name != POS_ARGS else name,
            type=annotation,
            default=value.default,
            help=DEFAULT_FORMATTED.format(value),
        )

    return parser.parse_args()


def create_config_with_args(config_class: Type[Config], args) -> Config:
    arg_dict = {
        name: getattr(args, name)
        for name in config_class.model_fields
        if hasattr(args, name) and getattr(args, name) != PydanticUndefined
    }
    if arg_dict.get(CONFIG_FILE) and Path(arg_dict[CONFIG_FILE]).exists():
        config = config_class(
            **{
                **arg_dict,
                **toml.load(arg_dict.get(CONFIG_FILE)),
            }
        )
    else:
        config = config_class(**arg_dict)
    for variable in config.model_fields:
        value = getattr(config, variable)
        if (
            isinstance(value, Path)
            and value.suffix == EMPTY
            and not value.exists()
        ):
            value.mkdir(parents=True)
    return config
