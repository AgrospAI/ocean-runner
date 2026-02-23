# Ocean Runner

[![PyPI](https://img.shields.io/pypi/v/ocean-runner?label=pypi&style=flat-square)](https://pypi.org/project/ocean-runner/)
[![Coverage](https://raw.githubusercontent.com/agrospai/ocean-runner/main/coverage.svg)](https://github.com/agrospai/ocean-runner)

Ocean Runner is a package that eases algorithm creation in the scope of OceanProtocol.

## Installation

```bash
pip install ocean-runner
# or
uv add ocean-runner
```

## Usage

### Annotated Minimal Example

```python
import random
from ocean_runner import Algorithm, EmptyAlgorithm

algorithm: EmptyAlgorithm[int] = Algorithm.create(None)


@algorithm.run
def run(_) -> int:
    return random.randint(0, 100)
```

This code snippet will:

- Read the OceanProtocol JobDetails from the environment variables and use default configuration file paths.
- Execute the default input validation function, assessing if there are input dids and ddos.
- Execute the run function.
- Execute the default saving function, storing the result in a "result.txt" file within the default outputs path.

### Not Annotated Minimal Example

If you do not care about static analysis tools, this snippet will run just fine.

```python
import random
from ocean_runner import Algorithm

algorithm = Algorithm.create(None)


@algorithm.run
def run(_):
    return random.randint(0, 100)
```

### Tuning

#### Application Config

The application configuration can be tweaked by passing a Config instance to its constructor.

```python
from ocean_runner import Algorithm, Config

algorithm = Algorithm.create(
    Config(
        custom_input: ... # dataclass
        # Custom algorithm parameters dataclass.

        logger: ... # type: logging.Logger
        # Custom logger to use.

        source_paths: ... # type: Iterable[Path]
        # Source paths to include in the PATH

        environment: ...
        # type: ocean_runner.Environment. Mock of environment variables.
    )
)
```

```python
import logging

from pydantic import BaseModel
from ocean_runner import Algorithm, Config


class CustomInput(BaseModel):
    foobar: string


logger = logging.getLogger(__name__)


algorithm = Algorithm.create(
    Config(
        custom_input=CustomInput,
        """
        Load the Algorithm's Custom Input into a CustomInput instance.
        """

        source_paths=[Path("/algorithm/src")],
        """
        Source paths to include in the PATH. '/algorithm/src' is the default since our templates place the algorithm source files there.
        """

        logger=logger,
        """
        Custom logger to use in the Algorithm.
        """

        environment=Environment(
            base_dir: "./_data",
            """
            Custom data path to use test data.
            """

            dids: '["17feb697190d9f5912e064307006c06019c766d35e4e3f239ebb69fb71096e42"]',
            """
            Dataset DID.
            """

            transformation_did: "1234",
            """
            Random transformation DID to use while testing.
            """

            secret: "1234",
            """
            Random secret to use while testing.
            """
        )
        """
        Should not be needed in production algorithms, used to mock environment variables, defaults to using env.
        """
    )
)

```

#### Behaviour Config

To fully configure the behaviour of the algorithm as in the [Minimal Example](#minimal-example), you can do it decorating your defined function as in the following fully annotated example (`Pyton >=3.12`), which features all the possible algorithm customization.

```python
from pathlib import Path
from typing import Sequence, Tuple

import pandas as pd
from oceanprotocol_job_details.domain import DID

from ocean_runner import Algorithm
from ocean_runner.runner import EmptyAlgorithm

type ResultT = Tuple[DID, pd.DataFrame]
type ResultsT = Sequence[ResultT]
algorithm: EmptyAlgorithm[ResultsT] = Algorithm.create(None)


@algorithm.on_error
def error_callback(_, ex: Exception):
    algorithm.logger.exception(ex)
    raise algorithm.Error() from ex


@algorithm.validate
def val(_) -> None:
    assert algorithm.job_details.files, "Empty input dir"


@algorithm.run
def run(_) -> ResultsT:
    def describe(df: pd.DataFrame) -> pd.DataFrame:
        return df.describe(include="all")

    return [
        (did, describe(pd.read_csv(file_path)))
        for did, file_path in algorithm.job_details.inputs()
    ]


@algorithm.save_results
def save(_, result: ResultsT, base: Path):
    for did, analysis in result:
        algorithm.logger.info(f"Descriptive statistics {did}: {result}")
        analysis.to_csv(base / f"{did}.csv")

```

### Default implementations

As seen in the minimal example, all methods implemented in `Algorithm` have a default implementation which will be commented here.

```python
.validate()

    """
    Will validate the algorithm's job detail instance, checking for the existence of:
    - `job_details.ddos`
    - `job_details.files`
    """

.run()

    """
    Has NO default implementation, must pass a callback that returns a result of any type.
    """

.save_results()

    """
    Stores the result of running the algorithm in "outputs/results.txt"
    """
```

### Job Details

To load the OceanProtocol JobDetails instance, the program will read some environment variables, they can be mocked passing an instance of `Environment` through the configuration of the algorithm.

Environment variables:

- `DIDS` (optional) Input dataset(s) DID's, must have format: `["abc..90"]`. Defaults to reading them automatically from the `DDO` data directory.
- `TRANSFORMATION_DID` (optional, default="DEFAULT"): Algorithm DID, must have format: `abc..90`.
- `SECRET` (optional, default="DEFAULT"): Algorithm secret.
- `BASE_DIR` (optional, default="/data"): Base path to the OceanProtocol data directories.
