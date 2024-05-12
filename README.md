# Vaquitapp backend

[![CI](https://github.com/VaquitApp/backend/actions/workflows/python-app.yml/badge.svg)](https://github.com/VaquitApp/backend/actions/workflows/python-app.yml)

## Dependencies

- make
- python3.11
- poetry

## Installation

After installing dependencies, run:

```bash
make install
```

## How to run

Run app locally with:

```bash
make run
```

***Note**: this will also install dependencies with poetry*

## Development pipeline

This project uses the *pytest* test suite in the CI pipeline.
To run tests locally, use the command `make test`.

To format or lint the project, run `make format` or `make lint` respectively.
