from __future__ import annotations

from dataclasses import InitVar, asdict, dataclass, field
from logging import Logger
from pathlib import Path
from typing import Callable, Generic, Self, TypeVar

from oceanprotocol_job_details import JobDetails

from ocean_runner.config import Config

JobDetailsT = TypeVar(
    "JobDetailsT",
)
ResultT = TypeVar("ResultT")


def default_error_callback(_: Algorithm, e: Exception) -> None:
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

    config: InitVar[Config | None] = None

    # Load from config
    logger: Logger = field(init=False)

    _job_details: JobDetails[JobDetailsT] = field(init=False)
    _result: ResultT | None = field(default=None, init=False)

    error_callback = default_error_callback

    def __post_init__(self, config: Config | None) -> None:
        config: Config = config or Config()

        if config.error_callback:
            self.error_callback = config.error_callback

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

        if isinstance(config.environment.base_dir, str):
            config.environment.base_dir = Path(config.environment.base_dir)

        if config.source_paths:
            import sys

            sys.path.extend([str(path.absolute()) for path in config.source_paths])
            self.logger.debug(f"Added [{len(config.source_paths)}] entries to PATH")

        self._job_details = JobDetails.load(
            _type=config.custom_input,
            base_dir=config.environment.base_dir,
            dids=config.environment.dids,
            transformation_did=config.environment.transformation_did,
            secret=config.environment.secret,
        )

        self.logger.info("Loaded JobDetails")
        self.logger.debug(asdict(self.job_details))

    class Error(RuntimeError): ...

    @property
    def job_details(self) -> JobDetails:
        if not self._job_details:
            raise Algorithm.Error("JobDetails not initialized or missing")
        return self._job_details

    @property
    def result(self) -> ResultT:
        if not self._result:
            raise Algorithm.Error("Result missing, run the algorithm first")
        return self._result

    def validate(
        self,
        callback: Callable[[Self], None] = default_validation,
    ) -> Self:
        self.logger.info("Validating instance...")
        try:
            callback(self)
        except Exception as e:
            self.error_callback(e)

        return self

    def run(
        self,
        callable: Callable[[Self], ResultT],
    ) -> Self:
        self.logger.info("Running algorithm...")
        try:
            self._result = callable(self)
        except Exception as e:
            self.error_callback(e)

        return self

    def save_results(
        self,
        callable: Callable[[ResultT, Path, Algorithm], None] = default_save,
        *,
        override_path: Path | None = None,
    ) -> None:
        self.logger.info("Saving results...")
        try:
            callable(
                results=self.result,
                base_path=override_path or self.job_details.paths.outputs,
                algorithm=self,
            )
        except Exception as e:
            self.error_callback(e)


__all__ = [Algorithm]
