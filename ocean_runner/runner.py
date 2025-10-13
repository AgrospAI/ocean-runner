from __future__ import annotations

from dataclasses import InitVar, asdict, dataclass, field
from logging import Logger
from pathlib import Path
from typing import Callable, Generic, TypeVar

from oceanprotocol_job_details import JobDetails

from ocean_runner.config import Config

JobDetailsT = TypeVar("JobDetailsT")
ResultT = TypeVar("ResultT")


def default_error_callback(_, e: Exception) -> None:
    raise e


def default_validation(algorithm: Algorithm) -> None:
    algorithm.logger.info("Validating input using default validation")
    assert algorithm.job_details.ddos, "DDOs missing"
    assert algorithm.job_details.files, "Files missing"


def default_save(*, result: ResultT, base: Path, algorithm: Algorithm) -> None:
    algorithm.logger.info("Saving results using default save")
    with open(base / "result.txt", "w+") as f:
        f.write(str(result))


@dataclass
class Algorithm(Generic[JobDetailsT, ResultT]):
    """
    A configurable algorithm runner that behaves like a FastAPI app:
      - You register `validate`, `run`, and `save_results` via decorators.
      - You execute the full pipeline by calling `app()`.
    """

    config: InitVar[Config | None] = None
    logger: Logger = field(init=False)
    _job_details: JobDetails[JobDetailsT] = field(init=False)
    _result: ResultT | None = field(default=None, init=False)

    # Decorator-registered callbacks
    _validate_fn: Callable[[Algorithm], None] | None = field(default=None, init=False)
    _run_fn: Callable[[Algorithm], ResultT] | None = field(default=None, init=False)
    _save_fn: Callable[[ResultT, Path, Algorithm], None] | None = field(
        default=None, init=False
    )
    _error_callback: Callable[[Algorithm, Exception], None] = field(
        default=default_error_callback, init=False
    )

    def __post_init__(self, config: Config | None) -> None:
        config: Config = config or Config()

        # Configure logger
        if config.logger:
            self.logger = config.logger
        else:
            import logging

            logging.basicConfig(
                level=logging.DEBUG,
                format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            self.logger = logging.getLogger("ocean_runner")

        # Normalize base_dir
        if isinstance(config.environment.base_dir, str):
            config.environment.base_dir = Path(config.environment.base_dir)

        # Extend sys.path for custom imports
        if config.source_paths:
            import sys

            sys.path.extend([str(path.absolute()) for path in config.source_paths])
            self.logger.debug(f"Added [{len(config.source_paths)}] entries to PATH")

        # Load job details
        self._job_details = JobDetails.load(
            _type=config.custom_input,
            base_dir=config.environment.base_dir,
            dids=config.environment.dids,
            transformation_did=config.environment.transformation_did,
            secret=config.environment.secret,
        )

        self.logger.info("Loaded JobDetails")
        self.logger.debug(asdict(self.job_details))

        self.config = config

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

    def validate(self, fn: Callable[[], None]) -> Callable[[], None]:
        self._validate_fn = fn
        return fn

    def run(self, fn: Callable[[], ResultT]) -> Callable[[], ResultT]:
        self._run_fn = fn
        return fn

    def save_results(self, fn: Callable[[ResultT, Path], None]) -> Callable:
        self._save_fn = fn
        return fn

    def on_error(self, fn: Callable[[Exception], None]) -> Callable:
        self._error_callback = fn
        return fn

    # ---------------------------
    # Execution Pipeline
    # ---------------------------

    def __call__(self) -> ResultT | None:
        """Executes the algorithm pipeline: validate → run → save_results."""
        try:
            # Validation step
            if self._validate_fn:
                self.logger.info("Running custom validation...")
                self._validate_fn()
            else:
                self.logger.info("Running default validation...")
                self.default_validation(self)

            # Run step
            if self._run_fn:
                self.logger.info("Running algorithm...")
                self._result = self._run_fn()
            else:
                self.logger.warning("No run() function defined. Skipping execution.")
                self._result = None

            # Save step
            if self._save_fn:
                self.logger.info("Saving results...")
                self._save_fn(
                    self._result,
                    self.job_details.paths.outputs,
                )
            else:
                self.logger.info("No save_results() defined. Using default.")
                default_save(
                    result=self._result,
                    base=self.job_details.paths.outputs,
                    algorithm=self,
                )

        except Exception as e:
            self.logger.exception("Error during algorithm execution")
            self._error_callback(e)

        return self._result
