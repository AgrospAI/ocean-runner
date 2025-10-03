# PyPI package template

This is a template to fasten the github repository creation of a PyPI package.

This template is opinionated, using the following:

- *uv* as a package manager.
- *pytest* as testing framework.
- *Github Actions* for package testing and uploading


To run the tests:

```bash
uv run pytest
```

## PyPi publish steps

To publish the built package into the PyPI repository, you need to setup the Github repository secrets with PyPI's api key as a Repository or Organization secret named `PYPI_TOKEN` (case insensitive).

The package will only be published upon manual Github release creation to avoid any unintended automatic publish after each individual main branch push or pull request.