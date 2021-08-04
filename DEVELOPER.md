# Aserto Python package development

## First time setup instructions

### pyenv
Follow the pyenv [installation instructions](https://github.com/pyenv/pyenv#installation). This tool will allow us to easily switch between different Python versions as needed.

*For all following steps make sure your shell is located in your local checkout of this repository.*

Then run:
```sh
pyenv install
```
This will install the version of Python specified by `.python-version`. This is the minimum supported version of Python for the SDK package.

### Poetry
Install [Poetry](https://python-poetry.org/docs/#installation). This must be [installed after pyenv](https://github.com/python-poetry/poetry/issues/651#issuecomment-864533910) has been installed. Poetry is used for managing package dependencies and publishing packages to [PyPI](https://pypi.org/).

Each package has its own `pyproject.toml` file. For every package you're developing on navigate to its directory and run:
```sh
poetry install
```

You can verify that your environment is correctly setup by running:
```sh
poetry run python -V
```
and verifying that the version number matches the one in `.python_version`.

## Commands

### Run tests
```sh
poetry run pytest
```

### Run the typechecker
```sh
poetry run mypy src
```

## Directory layout
TODO

## Running PeopleFinder example services
1. Navigate to the `peoplefinder_example` directory.
2. Follow the steps in `.env.example` to create a `.env` file.
3. Run:
```sh
poetry run flask run
```
4. Start only the front-end of the PeopleFinder service in your local checkout of https://github.com/aserto-demo/peoplefinder.
```
yarn spa
```