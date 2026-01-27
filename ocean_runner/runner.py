from __future__ import annotations

from dataclasses import InitVar, asdict, dataclass, field
from logging import Logger
from pathlib import Path
from typing import Callable, Generic, TypeVar

from oceanprotocol_job_details import JobDetails  # type: ignore

from ocean_runner.config import Config

InputT = TypeVar("InputT")
ResultT = TypeVar("ResultT")

ValidateFuncT = Callable[["Algorithm"], None]
RunFuncT = Callable[["Algorithm"], ResultT] | None
SaveFuncT = Callable[["Algorithm", ResultT, Path], None]
ErrorFuncT = Callable[["Algorithm", Exception], None]


def default_error_callback(algorithm: Algorithm, e: Exception) -> None:
    algorithm.logger.exception("Error during algorithm execution")
    raise e


def default_validation(algorithm: Algorithm) -> None:
    algorithm.logger.info("Validating input using default validation")
    assert algorithm.job_details.ddos, "DDOs missing"
    assert algorithm.job_details.files, "Files missing"


def default_save(algorithm: Algorithm, result: ResultT, base: Path) -> None:
    algorithm.logger.info("Saving results using default save")
    with open(base / "result.txt", "w+") as f:
        f.write(str(result))


@dataclass
class Algorithm(Generic[InputT, ResultT]):
    """
    A configurable algorithm runner that behaves like a FastAPI app:
      - You register `validate`, `run`, and `save_results` via decorators.
      - You execute the full pipeline by calling `app()`.
    """

    config: InitVar[Config[InputT] | None] = field(default=None)
    logger: Logger = field(init=False)
    _job_details: JobDetails[InputT] = field(init=False)
    _result: ResultT | None = field(default=None, init=False)

    # Decorator-registered callbacks
    _validate_fn: ValidateFuncT = field(
        default=default_validation,
        init=False,
        repr=False,
    )

    _run_fn: RunFuncT = field(
        default=None,
        init=False,
        repr=False,
    )

    _save_fn: SaveFuncT = field(
        default=default_save,
        init=False,
        repr=False,
    )

    _error_callback: ErrorFuncT = field(
        default=default_error_callback,
        init=False,
        repr=False,
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

        self.configuration = configuration

    class Error(RuntimeError): ...

    @property
    def job_details(self) -> JobDetails:
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
        self._validate_fn = fn
        return fn

    def run(self, fn: RunFuncT) -> RunFuncT:
        self._run_fn = fn
        return fn

    def save_results(self, fn: SaveFuncT) -> SaveFuncT:
        self._save_fn = fn
        return fn

    def on_error(self, fn: ErrorFuncT) -> ErrorFuncT:
        self._error_callback = fn
        return fn

    # ---------------------------
    # Execution Pipeline
    # ---------------------------

    def __call__(self) -> ResultT | None:
        """Executes the algorithm pipeline: validate → run → save_results."""
        # Load job details
        self._job_details = JobDetails.load(
            _type=self.configuration.custom_input,
            base_dir=self.configuration.environment.base_dir,
            dids=self.configuration.environment.dids,
            transformation_did=self.configuration.environment.transformation_did,
            secret=self.configuration.environment.secret,
        )

        self.logger.info("Loaded JobDetails")
        self.logger.debug(asdict(self.job_details))

        try:
            # Validation step
            self._validate_fn(self)

            # Run step
            if self._run_fn:
                self.logger.info("Running algorithm...")
                self._result = self._run_fn(self)
            else:
                self.logger.error("No run() function defined. Skipping execution.")
                self._result = None

            # Save step
            self._save_fn(self, self._result, self.job_details.paths.outputs)

        except Exception as e:
            self._error_callback(self, e)

        return self._result
