Contributing to Meetling
========================

## Development Dependencies

For development, the following additional requirements must be set up on your system:

* Pylint >= 1.4
* Sphinx >= 1.2

## Running Meetling in Debug Mode

To run Meetling in debug mode, type:

```sh
python3 -m meetling --debug
```

## Running the Tests

To run all unit tests, type:

```sh
python3 -m unittest discover -v
```

## Setting up Sample Data

To set up some sample data for Meetling, type:

```sh
./misc/sample.py
```

## Generating the Documentation

To build the Meetling documentation, type:

```sh
sphinx-build doc doc/build
```
