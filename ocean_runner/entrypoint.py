import argparse
import importlib
import sys

from pydantic import BaseModel, Field

from ocean_runner.runner import Algorithm


class CLIRunnerConfig(BaseModel):
    module: str = Field(
        default="algorithm.src",
        description="The python module path to import (e.g. 'algorithm.src')",
    )


def get_algorithm(module_path: str, name: str = "algorithm") -> Algorithm | None:
    module = importlib.import_module(module_path)

    attr_value = getattr(module, name)
    if isinstance(attr_value, Algorithm):
        return attr_value

    return None


def run_algorithm(config: CLIRunnerConfig) -> None:
    try:
        algorithm = get_algorithm(config.module)

        if not algorithm:
            raise RuntimeError(f"No Algorithm instance found in {config.module}")

        algorithm()
    except Exception as e:
        print(f"Failed to execute algorithm: {e}", file=sys.stderr)
        sys.exit(1)


def get_config() -> CLIRunnerConfig:
    parser = argparse.ArgumentParser(description="Ocean Runner CLI Entrypoint")
    parser.add_argument(
        "module",
        nargs="?",
        default="src.algorithm",
        help="The module path to import (e.g., 'src.algorithm')",
    )
    args = parser.parse_args()

    return CLIRunnerConfig.model_validate(vars(args))


def main() -> None:
    config = get_config()

    run_algorithm(config)
