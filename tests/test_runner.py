from pathlib import Path

from pytest import fixture, raises

from ocean_runner import Algorithm, Config, Environment


@fixture(scope="session", autouse=True)
def config():
    yield Config(environment=Environment(base_dir=Path("./_data")))


@fixture(scope="session", autouse=True)
def algorithm(config):
    yield Algorithm(config)


@fixture(scope="session", autouse=True)
def setup_algorithm(algorithm):

    @algorithm.validate
    def validate():
        assert algorithm.job_details.ddos, "Missing DDOs"
        assert algorithm.job_details.files, "Missing Files"

    @algorithm.run
    def run() -> int:
        return 123

    yield algorithm


def test_result(setup_algorithm, tmp_path):
    result_file = tmp_path / "results.txt"

    @setup_algorithm.save_results
    def save_results(result: int, *args) -> None:
        assert result is not None, "Missing result"
        assert result == 123

        with open(result_file, "w+") as f:
            f.write(str(result))

    setup_algorithm()

    assert result_file.exists(), "results.txt was not created"
    with open(result_file, "r") as f:
        assert f.read() == "123"


def test_exception(setup_algorithm):
    @setup_algorithm.run
    def run():
        raise Algorithm.Error()

    @setup_algorithm.on_error
    def callback(e):
        raise e

    with raises(Algorithm.Error):
        setup_algorithm()


def test_error_callback(setup_algorithm):
    count = 0

    @setup_algorithm.on_error
    def callback(_):
        nonlocal count
        count += 1

    @setup_algorithm.run
    def run():
        raise Algorithm.Error()

    setup_algorithm()
    assert count == 1, "Provided callback was not called"
