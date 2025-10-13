# ocean-runner

Ocean Runner is a package that eases algorithm creation in the scope of OceanProtocol.


## Installation

```bash
pip install ocean-runner
# or
uv add ocean-runner
```

## Usage

### Minimal Example

```python
import random
from ocean_runner import Algorithm

algorithm = Algorithm()


@algorithm.run
def run():
    return random.randint()


if __name__ == "__main__":
    algorithm()
```

This code snippet will:

- Read the OceanProtocol JobDetails from the environment variables and use default configuration file paths.
- Execute the run function.
- Execute the default saving function, storing the result in a "result.txt" file within the default outputs path.

### Tuning

#### Application Config

The application configuration can be tweaked by passing a Config instance to its constructor.

```python
from ocean_runner import Algorithm, Config

algorithm = Algorithm(
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

from ocean_runner import Algorithm, Config


@dataclass
class CustomInput:
    foobar: string 


logger = logging.getLogger(__name__)


algorithm = Algorithm(
    Config(
        custom_input: CustomInput,
        """
        Load the Algorithm's Custom Input into a CustomInput dataclass instance.
        """

        source_paths: [Path("/algorithm/src")],
        """
        Source paths to include in the PATH. '/algorithm/src' is the default since our templates place the algorithm source files there.
        """

        logger: logger,
        """
        Custom logger to use in the Algorithm.
        """

        environment: Environment(
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

To fully configure the behaviour of the algorithm as in the [Minimal Example](#minimal-example), you can do it decorating your defined function as in the following example, which features all the possible algorithm customization.

```python
from pathlib import Path

import pandas as pd
from ocean_runner import Algorithm

algorithm = Algorithm()


@algorithm.on_error
def error_callback(ex: Exception):
    algorithm.logger.exception(ex)
    raise algorithm.Error() from ex


@algorithm.validate
def val():
    assert algorithm.job_details.files, "Empty input dir"


@algorithm.run
def run() -> pd.DataFrame:
    _, filename = next(algorithm.job_details.next_path())
    return pd.read_csv(filename).describe(include="all")


@algorithm.save_results
def save(results: pd.DataFrame, path: Path):
    algorithm.logger.info(f"Descriptive statistics: {results}")
    results.to_csv(path / "results.csv")


if __name__ == "__main__":
    algorithm()
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
