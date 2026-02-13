import logging
from pathlib import Path

import aiofiles
from pytest import fixture, raises

from ocean_runner import Algorithm, Config, Environment


@fixture(scope="session")
def config():
    config = {"base_dir": "./_data"}
    environment = Environment(**config)
    yield Config(environment=environment)


@fixture(scope="function")
def algorithm(config):
    yield Algorithm(config=config)


@fixture(scope="function")
def setup_algorithm(algorithm):
    @algorithm.validate
    def validate(algorithm: Algorithm):
        assert algorithm.job_details.metadata, "Missing DDOs"
        assert algorithm.job_details.files, "Missing Files"

    @algorithm.run
    def run(algorithm: Algorithm) -> int:
        return 123

    yield algorithm


def test_defaults_without_log(config):
    logger = logging.getLogger(__name__)
    logger.disabled = True

    config = config.model_copy()
    config.logger = logger
    algorithm = Algorithm(config=config)

    with raises(Algorithm.Error):
        algorithm()
        algorithm.result


def test_empty_job_details_raises(config):
    algorithm = Algorithm(config=config)

    with raises(Algorithm.Error):
        algorithm._job_details = None
        algorithm.job_details

    with raises(Algorithm.Error):
        algorithm.result


def test_async(setup_algorithm: Algorithm):
    import asyncio

    @setup_algorithm.validate
    async def avalidation(algorithm: Algorithm):
        await asyncio.sleep(0.01)

    @setup_algorithm.run
    async def arun(algorithm: Algorithm) -> float:
        import random

        time = random.randint(0, 10) / 200
        await asyncio.sleep(time)

        return time

    setup_algorithm()

    assert 0 <= setup_algorithm.result <= 0.05


def test_result(setup_algorithm: Algorithm, tmp_path):
    result_file = tmp_path / "results.txt"

    @setup_algorithm.save_results
    async def save_results(algorithm: Algorithm, result: int, base: Path) -> None:
        assert result is not None, "Missing result"

        async with aiofiles.open(result_file, "w+") as f:
            await f.write(str(result))

    setup_algorithm()

    assert result_file.exists(), f"{result_file.name} was not created"


def test_exception(setup_algorithm):
    setup_algorithm.logger.disabled = True

    @setup_algorithm.run
    def run(algorithm: Algorithm):
        raise Algorithm.Error()

    with raises(Algorithm.Error):
        setup_algorithm()

    setup_algorithm.logger.disabled = False


def test_error_callback(setup_algorithm):
    count = 0

    @setup_algorithm.on_error
    def callback(algorithm, error):
        nonlocal count
        count += 1

    @setup_algorithm.run
    def run(algorithm):
        raise Algorithm.Error()

    setup_algorithm()
    assert count == 1, "Provided callback was not called"
