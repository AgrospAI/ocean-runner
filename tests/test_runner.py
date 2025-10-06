import tempfile
from logging import getLogger
from pathlib import Path

from pytest import fixture, raises

from ocean_runner import Algorithm, Config, Environment

logger = getLogger(__name__)


# Algorithm().run(lambda _: random.randint()).save_results()

algorithm: Algorithm


def config() -> Config:
    return Config(
        environment=Environment(
            base_dir=Path("./_data"),
            secret="1234",
            dids='["17feb697190d9f5912e064307006c06019c766d35e4e3f239ebb69fb71096e42"]',
            transformation_did="1234",
        )
    )


@fixture(scope="session", autouse=True)
def setup():

    global algorithm

    algorithm = Algorithm(config=config())

    yield

    logger.info("Ending session")


def test_validation():

    global algorithm

    # def validate(algorithm: Algorithm):
    #     assert algorithm.job_details.ddos, "Missing DDOs"
    #     assert algorithm.job_details.files, "Missing Files"

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


def test_run():

    global algorithm

    def run(algorithm: Algorithm) -> int:
        algorithm.logger.info("algorithmlication running...")
        return 123

    algorithm.run(run)


def test_result():

    global algorithm

    def save_results(results: int, **kwargs) -> None:
        assert results is not None, "Missing results"
        assert results == 123

    algorithm.save_results(save_results)


def test_result_into_file():

    global algorithm

    def save_results(results: int, base_path: Path, **kwargs) -> None:
        base_path.mkdir(exist_ok=True, parents=True)

        with tempfile.TemporaryFile(dir=base_path, mode="w+") as tf:
            tf.write(str(results))
            tf.seek(0)

            content = tf.read()
            assert content == "123"

    algorithm.save_results(save_results)


def test_exception():

    global algorithm

    CustomException = RuntimeError

    with raises(CustomException):

        def run(_):
            raise CustomException()

        algorithm.run(run)


def test_error_callback():

    count = 0

    def callback(_):
        nonlocal count
        count += 1

    conf = config()
    conf.error_callback = callback

    Algorithm(conf).run(lambda algorithm: algorithm.WILL_RAISE)

    assert count == 1, "Provided callback was not called"
