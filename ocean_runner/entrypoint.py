import argparse
import importlib
import os
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

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


def run_algorithm(config: CLIRunnerConfig) -> None:
    # Set the "base_dir" environment variable for oceanprotocol_job_details to load data from
    abs_base = config.base_dir.resolve()
    os.environ["base_dir"] = str(abs_base)

    # Ensure RW directories exist locally so the algorithm doesn't crash
    (abs_base / "outputs").mkdir(parents=True, exist_ok=True)
    (abs_base / "logs").mkdir(parents=True, exist_ok=True)

    algorithm = get_algorithm(config.module)

    if isinstance(algorithm, Algorithm):
        print(f"Launching algorithm from {config.module}")
        print(f"Base Directory: {abs_base}")
        algorithm()
    else:
        print(f"No algorithm instance found in {config.module}", file=sys.stderr)
        sys.exit(1)


def get_config() -> CLIRunnerConfig:
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
    args = parser.parse_args()

    return CLIRunnerConfig.model_validate(vars(args))


def main() -> None:
    print(f"--- Ocean Runner CLI v{get_version()} ---")

    config = get_config()

    run_algorithm(config)
