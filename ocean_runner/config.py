import os
from dataclasses import asdict, dataclass, field
from logging import Logger
from pathlib import Path
from typing import Callable, Iterable, Literal, TypeVar

T = TypeVar("T")


@dataclass
class Environment:
    """Environment variables mock"""

    base_dir: str | None = field(
        default_factory=lambda: os.environ.get("BASE_DIR", None),
    )
    """Base data directory, defaults to '/data'"""

    dids: str = field(
        default_factory=lambda: os.environ.get("DIDS"),
    )
    """Datasets DID's, format: '["XXXX"]'"""

    transformation_did: str = field(
        default_factory=lambda: os.environ.get("TRANSFORMATION_DID"),
    )
    """Transformation (algorithm) DID"""

    secret: str = field(
        default_factory=lambda: os.environ.get("SECRET"),
    )
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

    source_paths: Iterable[Path] = field(
        default_factory=lambda: [Path("/algorithm/src")]
    )
    """Paths that should be included so the code executes correctly"""

    environment: Environment = field(
        default_factory=lambda: Environment(),
    )
    """Mock of environment data"""
