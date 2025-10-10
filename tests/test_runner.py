from pathlib import Path

from pytest import fixture, raises

from ocean_runner import Algorithm, Config, Environment


@fixture(scope="session", autouse=True)
def config():
    yield Config(
        environment=Environment(
            base_dir=Path("./_data"),
        )
    )


@fixture(scope="session", autouse=True)
def algorithm(config):
    yield Algorithm(config)


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
    def run(_) -> int:
        return 123

    assert algorithm.run(run) is not None


def test_result(algorithm, tmp_path):
    result_file = tmp_path / "results.txt"

    def save_results(result: int, base: Path, **kwargs) -> None:
        assert result is not None, "Missing result"
        assert result == 123

        with open(base, "w+") as f:
            f.write(str(result))

    algorithm.save_results(save_results, override_path=result_file)

    assert result_file.exists(), "results.txt was not created"
    with open(result_file, "r") as f:
        assert f.read() == "123"


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
