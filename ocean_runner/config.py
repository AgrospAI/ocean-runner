from dataclasses import asdict, dataclass, field
from logging import Logger
import os
from typing import Callable, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class Environment:
    """Environment variables mock"""

    base_dir: str | None = field(default=os.environ.get("BASE_DIR", None))
    """Base data directory, defaults to '/data'"""

    dids: str = field(default=os.environ.get("DIDS"))
    """Datasets DID's, format: '["XXXX"]'"""

    transformation_did: str = field(default=os.environ.get("TRANSFORMATION_DID"))
    """Transformation (algorithm) DID"""

    secret: str = field(default=os.environ.get("SECRET"))
    """Super secret secret"""

    dict = asdict


@dataclass
class Config:
    """Algorithm overall configuration"""

    custom_input: T | None = None
    """Algorithm's custom input types, must be a dataclass_json"""

    error_callback: Callable[[Exception], None] = None
    """Callback to execute upon exceptions"""

    logger: Logger | None = None
    """Logger to use in the algorithm"""

    environment: Environment = Environment()
