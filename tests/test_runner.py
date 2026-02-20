import logging
from functools import partial
from pathlib import Path

import aiofiles
from pydantic import BaseModel
from pytest import fixture, raises

from ocean_runner import Algorithm, Config, Environment
from ocean_runner.runner import EmptyAlgorithm, ParametrizedAlgorithm


class CustomInput(BaseModel):
    example: str
    isTrue: bool


@fixture(scope="session")
def config():
    config = {"base_dir": "./_data"}
    environment = Environment(**config)
    yield Config(environment=environment)


@fixture(scope="function")
def algorithm(config: Config):
    yield Algorithm.create(config=config)


@fixture(scope="function")
def setup_algorithm(algorithm):
    @algorithm.validate
    def _(algorithm: Algorithm):
        assert algorithm.job_details.metadata, "Missing DDOs"
        assert algorithm.job_details.files, "Missing Files"

    @algorithm.run
    def _(_) -> int:
        return 123

    yield algorithm


def test_algorithm_without_config_raises():
    Algorithm.create()


def test_defaults_without_log(config):
    logger = logging.getLogger(__name__)
    logger.disabled = True

    config = config.model_copy()
    config.logger = logger
    algorithm = Algorithm.create(config=config)

    with raises(Algorithm.Error):
        algorithm()
        algorithm.result


def test_parametrized_job_details(config: Config[CustomInput]):
    config = config.model_copy()
    config.custom_input = CustomInput

    algorithm: ParametrizedAlgorithm[CustomInput, int] = Algorithm.create(config)

    algorithm.run(partial)

    algorithm()  # Must run to load job_details

    assert isinstance(algorithm, ParametrizedAlgorithm)
    assert algorithm.job_details.input_parameters.example == "data"
    assert algorithm.job_details.input_parameters.isTrue


def test_empty_job_details_raises(config):
    algorithm = Algorithm.create(config=config)

    assert isinstance(algorithm, EmptyAlgorithm)

    with raises(Algorithm.Error):
        algorithm.result


def test_async(setup_algorithm: Algorithm):
    import asyncio

    @setup_algorithm.validate
    async def _(_):
        await asyncio.sleep(0.01)

    @setup_algorithm.run
    async def _(_) -> float:
        import random

        time = random.randint(0, 10) / 200
        await asyncio.sleep(time)

        return time

    setup_algorithm()

    assert 0 <= setup_algorithm.result <= 0.05


def test_result(setup_algorithm: Algorithm, tmp_path):
    result_file = tmp_path / "results.txt"

    @setup_algorithm.save_results
    async def _(_, result: int, base: Path) -> None:
        assert result is not None, "Missing result"

        async with aiofiles.open(result_file, "w+") as f:
            await f.write(str(result))

    setup_algorithm()

    assert result_file.exists(), f"{result_file.name} was not created"


def test_exception(setup_algorithm):
    setup_algorithm.logger.disabled = True

    @setup_algorithm.run
    def _(_):
        raise Algorithm.Error()

    with raises(Algorithm.Error):
        setup_algorithm()

    setup_algorithm.logger.disabled = False


def test_error_callback(setup_algorithm):
    count = 0

    @setup_algorithm.on_error
    def _(_, __):
        nonlocal count
        count += 1

    @setup_algorithm.run
    def _(_):
        raise Algorithm.Error()

    setup_algorithm()
    assert count == 1, "Provided callback was not called"
