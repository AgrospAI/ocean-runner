import argparse
import importlib
import os
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Sequence

from pydantic import BaseModel, Field

from ocean_runner.runner import Algorithm


def get_version() -> str:
    try:
        return version("ocean-runner")
    except PackageNotFoundError:
        return "unknown (local/uninstalled)"


class CLIRunnerConfig(BaseModel):
    module: str = Field(
        default="algorithm.src",
        description="The python module path to import (e.g. 'algorithm.src')",
    )

    base_dir: Path = Field(default=Path("../_data"), description="Base data path")

    def model_post_init(self, context, /) -> None:
        if not self.base_dir.exists():
            raise FileNotFoundError(
                f"The given base data directory does not exist {self.base_dir}"
            )

        return super().model_post_init(context)


def get_algorithm(module_path: str) -> Algorithm | None:
    # Add cwd to sys.path so "algorithm.src" can be found
    if os.getcwd() not in sys.path:
        sys.path.append(os.getcwd())

    try:
        module = importlib.import_module(module_path)

        algorithm = getattr(module, "algorithm")

        if not isinstance(algorithm, Algorithm):
            return None

        return algorithm
    except (ImportError, AttributeError) as e:
        print(f"Error loading algorithm from {module_path}: {e}", file=sys.stderr)

    return None


def setup_environment(base_dir: Path) -> None:
    abs_base = base_dir.resolve()
    # Set the "base_dir" environment variable for oceanprotocol_job_details to load data from
    os.environ["base_dir"] = str(abs_base)

    # Ensure RW directories exist locally so the algorithm doesn't crash
    (abs_base / "outputs").mkdir(parents=True, exist_ok=True)
    (abs_base / "logs").mkdir(parents=True, exist_ok=True)


def run_algorithm(config: CLIRunnerConfig) -> None:
    setup_environment(config.base_dir)

    algorithm = get_algorithm(config.module)

    if isinstance(algorithm, Algorithm):
        print(f"Launching algorithm from {config.module}")
        print(f"Base Directory: {config.base_dir}")
        algorithm()
    else:
        print(f"No algorithm instance found in {config.module}", file=sys.stderr)
        sys.exit(1)


def run_tests(config: CLIRunnerConfig, args: Sequence[str]) -> None:
    import pytest

    print(f"Preparing Test Environment at: {config.base_dir.resolve()}")
    setup_environment(config.base_dir)

    sys.path.append(str(Path.cwd()))

    exit_code = pytest.main([*args])
    sys.exit(exit_code)


def get_config(args: Sequence[str]) -> CLIRunnerConfig:
    parser = argparse.ArgumentParser(description="Ocean Runner CLI Entrypoint")
    parser.add_argument(
        "module",
        nargs="?",
        default="src.algorithm",
        help="The module path to import (e.g., 'algorithm.src')",
    )
    parser.add_argument(
        "--base-dir",
        "-b",
        default="../_data",
        help="The base data directory path",
    )

    return CLIRunnerConfig.model_validate(vars(parser.parse_args(args)))


def setup(args: Sequence[str]) -> CLIRunnerConfig:
    print(f"--- Ocean Runner CLI v{get_version()} ---")

    return get_config(args)


def main() -> None:
    config = setup(sys.argv)
    run_algorithm(config)


def main_test() -> None:
    try:
        sep_index = sys.argv.index("--")
        wrapper_args = sys.argv[1:sep_index]
        pytest_argv = sys.argv[sep_index + 1 :]
    except ValueError:
        # If '--' is not present, everything is a wrapper arg
        wrapper_args = sys.argv[1:]
        pytest_argv = []

    final_args = pytest_argv if pytest_argv else ["tests"]

    config = setup(wrapper_args)
    run_tests(config, final_args)
