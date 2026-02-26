from importlib.metadata import PackageNotFoundError
from unittest.mock import MagicMock, patch

import pytest

from ocean_runner.entrypoint import (
    CLIRunnerConfig,
    get_algorithm,
    get_config,
    get_version,
    main,
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
    return_value=CLIRunnerConfig(module="test.mod", base_dir="./_data"),
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
    return_value=CLIRunnerConfig(module="bad.mod", base_dir="./_data"),
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
