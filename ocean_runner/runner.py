from __future__ import annotations

import asyncio
from abc import abstractmethod
from functools import cached_property
from logging import Logger
from pathlib import Path
from typing import (
    Any,
    Callable,
    Coroutine,
    Dict,
    Generic,
    TypeAlias,
    TypeVar,
    cast,
    overload,
    override,
)

from oceanprotocol_job_details import (
    EmptyJobDetails,
    ParametrizedJobDetails,
    load_job_details,
    run_in_executor,
)
from oceanprotocol_job_details.ocean import _BaseJobDetails
from pydantic import BaseModel, JsonValue
from returns.result import Success, Failure

from ocean_runner.config import Config

InputT = TypeVar("InputT", bound=BaseModel | None)
ResultT = TypeVar("ResultT")
T = TypeVar("T")


Algo: TypeAlias = "Algorithm[InputT, ResultT]"
ValidateFuncT: TypeAlias = Callable[[Algo], None | Coroutine[Any, Any, None] | None]
RunFuncT: TypeAlias = Callable[[Algo], ResultT | Coroutine[Any, Any, ResultT]]
SaveFuncT: TypeAlias = Callable[[Algo, ResultT, Path], Coroutine[Any, Any, None] | None]
ErrorFuncT: TypeAlias = Callable[[Algo, Exception], Coroutine[Any, Any, None] | None]


class NoParameters(BaseModel): ...


def default_error_callback(
    algorithm: Algorithm[InputT, ResultT],
    error: Exception,
) -> None:
    algorithm.logger.error("Error during algorithm execution")
    raise error


def default_validation(algorithm: Algorithm[InputT, ResultT]) -> None:
    algorithm.logger.info("Validating input using default validation")
    assert algorithm.job_details.metadata, "DDOs missing"
    assert algorithm.job_details.files, "Files missing"


def default_run(algorithm: Algorithm[InputT, ResultT]) -> ResultT:
    raise algorithm.Error("You must register a 'run' method")


async def default_save(
    algorithm: Algorithm[InputT, ResultT],
    result: ResultT,
    base: Path,
) -> None:
    from aiofiles import open

    algorithm.logger.info("Saving results using default save")

    async with open(base / "result.txt", "w+") as f:
        await f.write(str(result))


class Functions(Generic[InputT, ResultT]):
    def __init__(self) -> None:
        self.validate: ValidateFuncT = default_validation
        self.run: RunFuncT = default_run
        self.save: SaveFuncT = default_save
        self.error: ErrorFuncT = default_error_callback


class Algorithm(Generic[InputT, ResultT]):
    """
    A configurable algorithm runner that behaves like a FastAPI app:
      - You register `validate`, `run`, and `save_results` via decorators.
      - You execute the full pipeline by calling `app()`.
    """

    def __init__(self, configuration: Config[InputT]) -> None:
        self._initialize_internal_state(configuration)
        self._result: ResultT | None = None
        self._functions: Functions[InputT, ResultT] = Functions()

        self.logger: Logger

    @overload
    @classmethod
    def create(cls, config: Config[InputT]) -> ParametrizedAlgorithm[InputT, ResultT]:
        pass  # pragma: no cover

    @overload
    @classmethod
    def create(cls, config: Config[None]) -> EmptyAlgorithm[ResultT]:
        pass  # pragma: no cover

    @overload
    @classmethod
    def create(cls, config: None) -> EmptyAlgorithm[ResultT]:
        pass  # pragma: no cover

    @classmethod
    def create(cls, config: Any = None) -> Any:
        """
        Factory method, inspects the config.custom_input to decide
        which Algorithm subclass to instantiate.
        """

        if config is None:
            config = Config()

        if config.custom_input is None:
            return EmptyAlgorithm[ResultT](config)
        return ParametrizedAlgorithm[InputT, ResultT](config)

    def _initialize_internal_state(self, configuration: Config) -> None:
        if configuration.logger:
            self.logger = configuration.logger
        else:
            import logging

            logging.basicConfig(
                level=logging.DEBUG,
                format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            self.logger = logging.getLogger(__name__)

        # Normalize base_dir
        if isinstance(configuration.environment.base_dir, str):
            configuration.environment.base_dir = Path(
                configuration.environment.base_dir
            )

        # Extend sys.path for custom imports
        if configuration.source_paths:
            import sys

            sys.path.extend(
                [str(path.absolute()) for path in configuration.source_paths]
            )
            self.logger.debug(
                f"Added [{len(configuration.source_paths)}] entries to PATH"
            )

        self.configuration: Config[InputT] = configuration

    class Error(RuntimeError): ...

    @property
    def result(self) -> ResultT:
        if self._result is None:
            raise Algorithm.Error("Result missing, run the algorithm first")
        return self._result

    # ---------------------------
    # Decorators (FastAPI-style)
    # ---------------------------

    def validate(self, fn: ValidateFuncT) -> ValidateFuncT:
        self._functions.validate = fn
        return fn

    def run(self, fn: RunFuncT) -> RunFuncT:
        self._functions.run = fn
        return fn

    def save_results(self, fn: SaveFuncT) -> SaveFuncT:
        self._functions.save = fn
        return fn

    def on_error(self, fn: ErrorFuncT) -> ErrorFuncT:
        self._functions.error = fn
        return fn

    # ---------------------------
    # Execution Pipeline
    # ---------------------------

    async def execute(self) -> ResultT | None:
        env = self.configuration.environment
        config: Dict[str, JsonValue] = {
            "base_dir": str(env.base_dir),
            "dids": env.dids,
            "secret": env.secret,
            "transformation_did": env.transformation_did,
        }
        config = {k: v for k, v in config.items() if v is not None}

        custom_input = None
        if self.configuration.custom_input is not NoParameters:
            custom_input = self.configuration.custom_input

        self._job_details = load_job_details(custom_input, config)
        self.logger.info("Loaded JobDetails")

        try:
            await run_in_executor(
                self._functions.validate,
                self,
            )

            self._result = await run_in_executor(
                self._functions.run,
                self,
            )

            self._job_details.paths.outputs.mkdir(exist_ok=True)

            await run_in_executor(
                self._functions.save,
                self,
                self._result,
                self._job_details.paths.outputs,
            )

        except Algorithm.Error as e:
            await run_in_executor(self._functions.error, self, e)

        return self._result

    @abstractmethod
    @cached_property
    def job_details(self) -> _BaseJobDetails[InputT]: ...

    def __call__(self) -> ResultT | None:
        """Executes the algorithm pipeline: validate → run → save_results."""
        return asyncio.run(self.execute())


class ParametrizedAlgorithm(Algorithm[InputT, ResultT]):
    """For algorithms with validated custom parameters."""

    @override
    @cached_property
    def job_details(self) -> ParametrizedJobDetails[InputT]:
        match self._job_details.read():
            case Success(parametrized_job_details):
                return parametrized_job_details
            case Failure(error):
                raise error

        return self._job_details.read().unwrap()


class EmptyAlgorithm(Algorithm[None, ResultT]):
    """For algorithms with no custom parameters"""

    @override
    @cached_property
    def job_details(self) -> EmptyJobDetails[None]:
        return cast(EmptyJobDetails[None], self._job_details)
