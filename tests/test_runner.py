import tempfile
from pathlib import Path
from pytest import fixture, raises

from ocean_runner import Algorithm, Config, Environment
from ocean_runner.runtime_mode import RuntimeMode


@fixture(scope="session", autouse=True)
def logger():
    from logging import getLogger

    yield getLogger(__name__)


@fixture(scope="session", autouse=True)
def config():
    yield Config(
        environment=Environment(
            base_dir=Path("./_data"),
            secret="1234",
            dids='["17feb697190d9f5912e064307006c06019c766d35e4e3f239ebb69fb71096e42"]',
            transformation_did="1234",
        )
    )


@fixture(scope="session", autouse=True)
def algorithm(logger, config):
    algorithm = Algorithm(config)

    yield algorithm

    logger.info("Ending session")


def test_validation(algorithm):
    def raise_error(msg: str):
        raise RuntimeError(msg)

    algorithm.validate(
        lambda algorithm: all(
            (
                algorithm.job_details.ddos or raise_error("Missing DDOs"),
                algorithm.job_details.ddos or raise_error("Missing DDOs"),
            )
        )
    )


def test_run(algorithm):
    def run(algorithm: Algorithm) -> int:
        algorithm.logger.info("algorithmlication running...")
        return 123

    algorithm.run(run)


def test_result(algorithm):
    def save_results(results: int, **kwargs) -> None:
        assert results is not None, "Missing results"
        assert results == 123

    algorithm.save_results(save_results)


def test_result_into_file(algorithm):
    def save_results(results: int, base_path: Path, **kwargs) -> None:
        base_path.mkdir(exist_ok=True, parents=True)

        with tempfile.TemporaryFile(dir=base_path, mode="w+") as tf:
            tf.write(str(results))
            tf.seek(0)

            content = tf.read()
            assert content == "123"

    algorithm.save_results(save_results)


def test_exception(algorithm):
    CustomException = RuntimeError

    with raises(CustomException):

        def run(_):
            raise CustomException()

        algorithm.run(run)


def test_error_callback(config):

    count = 0

    def callback(_):
        nonlocal count
        count += 1

    config.error_callback = callback

    Algorithm(config).run(lambda algorithm: algorithm.WILL_RAISE)

    assert count == 1, "Provided callback was not called"


def test_runtime_dev(config):

    config.environment.runtime = "dev"

    assert Algorithm(config)._runtime is RuntimeMode.DEV


def test_runtime_test(config):
    config.environment.runtime = "test"
    assert Algorithm(config)._runtime is RuntimeMode.TEST
