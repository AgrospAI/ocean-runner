# ocean-runner

Ocean Runner is a package that brings a fluent API for APP creation and running in the scope of OceanProtocol.


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
from ocean_runner import Algorithm, Config


Algorithm().run(lambda _: random.randint()).save_results()    
```

To use minimally the API, you can just provide a callback to the run method, defaulting for the rest of behaviours. This code snippet will:

- Read the OceanProtocol JobDetails from the environment variables and use default file paths.
- Generate a random integer.
- Store the result in a "result.txt" file within the default outputs path.

### Tuning

#### Application Config

The application configuration can be tweaked by passing a Config instance to its' constructor.

```python
Algorithm(
    Config(
        custom_input: ... # dataclass
        # Custom algorithm parameters dataclass.
        
        error_callback: ... # Callable[[Exception], None]
        # Callback to run on exceptions.
        
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


@dataclass
class CustomInput:
    foobar: string 


logger = logging.getLogger(__name__)


Algorithm(
    Config(
        custom_input: CustomInput,
        """
        Load the Algorithm's Custom Input into a CustomInput dataclass instance.
        """

        error_callback: lambda ex: logger.exception(ex),
        """
        Run this callback when an exception is caught
        NOTE: it's not recommended to catch exceptions this way. Should re-raise and halt the execution.
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

## Default behaviours

### Default implementations

As seen in the minimal example, all methods implemented in `Algorithm` have a default implementation which will be commented here.

```python

(
    Algorithm()
    
        """
        Default constructor, will use default values of Config.
        """
    
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

)


```

### Job Details

To load the OceanProtocol JobDetails instance, the program will read some environment variables, they can be mocked passing an instance of `Environment` through the configuration of the algorithm.

Environment variables:
- `DIDS` Input dataset(s) DID's, must have format: `["abc..90"]`
- `TRANSFORMATION_DID` Algorithm DID, must have format: `abc..90`
- `SECRET` Algorithm secret.
- `BASE_DIR` (optional, default="/data"): Base path to the OceanProtocol data directories.
