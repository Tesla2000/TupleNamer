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


class Config(BaseModel):
    _root: Path = Path(__file__).parent
    pos_args: list[str] = Field(default_factory=list)
    config_file: Optional[Path] = None
    env_file_path: Path = Path(".env")


def parse_arguments(config_class: Type[Config]):
    parser = CustomArgumentParser(
        description="Configure the application settings."
    )

    for name, value in config_class.model_fields.items():
        if name.startswith("_"):
            continue
        annotation = value.annotation
        if len(getattr(value.annotation, "__args__", [])) > 1:
            annotation = next(filter(None, value.annotation.__args__))
        if get_origin(value.annotation) == Literal:
            annotation = str
        parser.add_argument(
            f"--{name}" if name != "pos_args" else name,
            type=annotation,
            default=value.default,
            help=f"Default: {value}",
        )

    return parser.parse_args()


def create_config_with_args(config_class: Type[Config], args) -> Config:
    arg_dict = {
        name: getattr(args, name)
        for name in config_class.model_fields
        if hasattr(args, name) and getattr(args, name) != PydanticUndefined
    }
    if arg_dict.get("config_file") and Path(arg_dict["config_file"]).exists():
        config = config_class(
            **{
                **arg_dict,
                **toml.load(arg_dict.get("config_file")),
            }
        )
    else:
        config = config_class(**arg_dict)
    for variable in config.model_fields:
        value = getattr(config, variable)
        if (
            isinstance(value, Path)
            and value.suffix == ""
            and not value.exists()
        ):
            value.mkdir(parents=True)
    return config
