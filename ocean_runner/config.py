from enum import StrEnum, auto
from logging import Logger
from pathlib import Path
from typing import Generic, Sequence, Type, TypeVar

from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings

InputT = TypeVar("InputT", bound=BaseModel | None)

DEFAULT = "DEFAULT"


class Keys(StrEnum):
    SECRET = auto()
    BASE_DIR = auto()
    TRANSFORMATION_DID = auto()
    DIDS = auto()


class Environment(BaseSettings):
    """Environment configuration loaded from environment variables"""

    base_dir: str | Path = Field(
        default_factory=lambda: Path("/data"),
        validation_alias=Keys.BASE_DIR.value,
        description="Base data directory, defaults to '/data'",
    )

    dids: str | None = Field(
        default=None,
        validation_alias=Keys.DIDS.value,
        description='Datasets DID\'s, format: ["XXXX"]',
    )

    transformation_did: str = Field(
        default=DEFAULT,
        validation_alias=Keys.TRANSFORMATION_DID.value,
        description="Transformation (algorithm) DID",
    )

    secret: str = Field(
        default=DEFAULT,
        validation_alias=Keys.SECRET.value,
        description="Super secret secret",
    )


class Config(BaseModel, Generic[InputT]):
    """Algorithm overall configuration"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    custom_input: Type[InputT] | None = Field(
        default=None,
        description="Algorithm's custom input types, must be a dataclass_json",
    )

    logger: Logger | None = Field(
        default=None,
        description="Logger to use in the algorithm",
    )

    source_paths: Sequence[Path] = Field(
        default_factory=lambda: [Path("/algorithm/src")],
        description="Paths that should be included so the code executes correctly",
    )

    environment: Environment = Field(
        default_factory=Environment, description="Environment configuration"
    )
