from pathlib import Path

import aiofiles
from pytest import fixture, raises

from ocean_runner import Algorithm, Config, Environment


@fixture(scope="session")
def config():
    config = {"base_dir": Path("./_data")}
    environment = Environment(**config)
    yield Config(environment=environment)


@fixture(scope="function")
def algorithm(config):
    yield Algorithm(config=config)


@fixture(scope="function")
def setup_algorithm(algorithm):
    @algorithm.validate
    def validate(algorithm: Algorithm):
        assert algorithm.job_details.ddos, "Missing DDOs"
        assert algorithm.job_details.files, "Missing Files"

    @algorithm.run
    def run(algorithm: Algorithm) -> int:
        return 123

    yield algorithm


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
    @setup_algorithm.run
    def run(algorithm: Algorithm):
        raise Algorithm.Error()

    @setup_algorithm.on_error
    def callback(algorithm: Algorithm, error: Exception):
        raise error

    with raises(Algorithm.Error):
        setup_algorithm()


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
