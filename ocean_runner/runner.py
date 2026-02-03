from __future__ import annotations

import asyncio
from dataclasses import InitVar, dataclass, field
from logging import Logger
from pathlib import Path
from typing import Any, Callable, Coroutine, Dict, Generic, TypeAlias, TypeVar

import aiofiles
from oceanprotocol_job_details import JobDetails, load_job_details, run_in_executor
from pydantic import BaseModel, JsonValue

from ocean_runner.config import Config

InputT = TypeVar("InputT", bound=BaseModel)
ResultT = TypeVar("ResultT")
T = TypeVar("T")


Algo: TypeAlias = "Algorithm[InputT, ResultT]"
ValidateFuncT: TypeAlias = Callable[[Algo], None | Coroutine[Any, Any, None] | None]
RunFuncT: TypeAlias = Callable[[Algo], ResultT | Coroutine[Any, Any, ResultT]]
SaveFuncT: TypeAlias = Callable[[Algo, ResultT, Path], Coroutine[Any, Any, None] | None]
ErrorFuncT: TypeAlias = Callable[[Algo, Exception], Coroutine[Any, Any, None] | None]


def default_error_callback(
    algorithm: Algorithm[InputT, ResultT],
    error: Exception,
) -> None:
    algorithm.logger.exception("Error during algorithm execution")
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
    algorithm.logger.info("Saving results using default save")
    async with aiofiles.open(base / "result.txt", "w+") as f:
        await f.write(str(result))


@dataclass(slots=True)
class Functions(Generic[InputT, ResultT]):
    validate: ValidateFuncT = field(default=default_validation, init=False)
    run: RunFuncT = field(default=default_run, init=False)
    save: SaveFuncT = field(default=default_save, init=False)
    error: ErrorFuncT = field(default=default_error_callback, init=False)


@dataclass
class Algorithm(Generic[InputT, ResultT]):
    """
    A configurable algorithm runner that behaves like a FastAPI app:
      - You register `validate`, `run`, and `save_results` via decorators.
      - You execute the full pipeline by calling `app()`.
    """

    config: InitVar[Config[InputT] | None] = field(default=None)

    logger: Logger = field(init=False, repr=False)

    _job_details: JobDetails[InputT] = field(init=False)
    _result: ResultT | None = field(default=None, init=False)
    _functions: Functions[InputT, ResultT] = field(
        default_factory=Functions, init=False, repr=False
    )

    def __post_init__(self, config: Config[InputT] | None) -> None:
        configuration = config or Config()

        # Configure logger
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
    def job_details(self) -> JobDetails[InputT]:
        if not self._job_details:
            raise Algorithm.Error("JobDetails not initialized or missing")
        return self._job_details

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

        self._job_details = load_job_details(config, self.configuration.custom_input)

        self.logger.info("Loaded JobDetails")
        self.logger.debug(self.job_details.model_dump())

        try:
            await run_in_executor(self._functions.validate, self)
            self._result = await run_in_executor(self._functions.run, self)
            await run_in_executor(
                self._functions.save,
                algorithm=self,
                result=self._result,
                base=self.job_details.paths.outputs,
            )

        except Exception as e:
            await run_in_executor(self._functions.error, self, e)

        return self._result

    def __call__(self) -> ResultT | None:
        """Executes the algorithm pipeline: validate → run → save_results."""
        return asyncio.run(self.execute())
