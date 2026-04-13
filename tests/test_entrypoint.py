import sys
from importlib.metadata import PackageNotFoundError
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ocean_runner.entrypoint import (
    CLIRunnerConfig,
    get_algorithm,
    get_config,
    get_version,
    main,
    main_test,
    run_tests,
)
from ocean_runner.runner import Algorithm


class MockAlgo(Algorithm):
    def __init__(self):
        self.called = False

    def __call__(self):
        self.called = True


def test_config_validation_custom_args():
    """Test that CLIRunnerConfig accepts custom module paths."""

    config = get_config(["custom.path", "--base-dir", "./_data"])
    assert config.module == "custom.path"
    assert config.base_dir.exists()


@patch("pathlib.Path.exists", return_value=False)
def test_config_validation_raises_if_bad_path(mock_exists):
    with pytest.raises(FileNotFoundError):
        get_config(["custom.path", "--base-dir", "./_data"])


@patch("importlib.import_module")
def test_get_algorithm_success(mock_import):
    """Test that get_algorithm correctly finds an Algorithm instance."""

    mock_module = MagicMock()
    mock_instance = MockAlgo()
    mock_module.algorithm = mock_instance

    mock_import.return_value = mock_module

    result = get_algorithm("some.module")
    assert result is mock_instance


@patch("importlib.import_module")
def test_get_algorithm_no_instance(mock_import):
    """Test behavior when no Algorithm instance exists in the module."""
    mock_module = MagicMock()
    mock_module.algorithm = "just a string"
    mock_import.return_value = mock_module
    result = get_algorithm("some.module")

    assert result is None


@patch("ocean_runner.entrypoint.get_algorithm")
@patch(
    "ocean_runner.entrypoint.get_config",
    return_value=CLIRunnerConfig(module="test.mod", base_dir=Path("./_data")),
)
def test_main_execution_flow(mock_get_config, mock_get_algo):
    """Test the full main loop triggers the algorithm call."""

    mock_algo = MagicMock(spec=Algorithm)
    mock_get_algo.return_value = mock_algo

    main()

    # Verify the algorithm was actually called
    mock_algo.assert_called_once()


@patch("ocean_runner.entrypoint.get_algorithm", return_value=None)
@patch(
    "ocean_runner.entrypoint.get_config",
    return_value=CLIRunnerConfig(module="bad.mod", base_dir=Path("./_data")),
)
def test_main_failure_exit(mock_get_config, mock_get_algo):
    """Test that the runner exits with code 1 if no algorithm is found."""
    with pytest.raises(SystemExit) as excinfo:
        main()
    assert excinfo.value.code == 1


@patch("ocean_runner.entrypoint.version", return_value="123")
def test_version(mock_version):
    assert "123" in get_version()


@patch("ocean_runner.entrypoint.version", side_effect=PackageNotFoundError())
def test_version_failing(mock_version):
    assert "unknown" in get_version()


@patch("importlib.import_module", side_effect=ImportError())
def test_import_algorithm_error(mock_import, capsys):
    result = get_algorithm("test")

    captured = capsys.readouterr()

    assert result is None
    assert "Error loading" in captured.err


def test_import_not_in_path():
    fake_cwd = "/fake/path"

    with patch("os.getcwd", return_value=fake_cwd):
        with patch("sys.path", []):
            get_algorithm("some.module")

            assert fake_cwd in sys.path


@patch("sys.exit")
@patch("pytest.main", return_value=0)
@patch("ocean_runner.entrypoint.setup_environment")
def test_run_tests(mock_setup_env, mock_pytest_main, mock_exit, capsys, tmp_path):
    config = MagicMock()
    config.base_dir = tmp_path

    args = ["-k", "test_something"]

    run_tests(config, args)

    # Check environment setup
    mock_setup_env.assert_called_once_with(config.base_dir)

    # Check pytest execution
    mock_pytest_main.assert_called_once_with(args)

    # Check exit called with pytest result
    mock_exit.assert_called_once_with(0)

    # Check printed message
    captured = capsys.readouterr()
    assert "Preparing Test Environment at:" in captured.out


@patch("ocean_runner.entrypoint.run_tests")
@patch("ocean_runner.entrypoint.setup")
def test_main_test_with_separator(mock_setup, mock_run_tests):
    mock_config = MagicMock()
    mock_setup.return_value = mock_config

    test_argv = ["prog", "--config", "dev", "--", "-k", "test_api"]

    with patch("sys.argv", test_argv):
        main_test()

    mock_setup.assert_called_once_with(["--config", "dev"])
    mock_run_tests.assert_called_once_with(mock_config, ["-k", "test_api"])


@patch("ocean_runner.entrypoint.run_tests")
@patch("ocean_runner.entrypoint.setup")
def test_main_test_without_separator(mock_setup, mock_run_tests):
    mock_config = MagicMock()
    mock_setup.return_value = mock_config

    test_argv = ["prog", "--config", "dev"]

    with patch("sys.argv", test_argv):
        main_test()

    mock_setup.assert_called_once_with(["--config", "dev"])
    mock_run_tests.assert_called_once_with(mock_config, ["tests"])
