# Contributing to Meetling

## Installing development dependencies

To install the development dependencies for Meetling, type:

```sh
pip install --user -U -r requirements-dev.txt
```

## Running Meetling in Debug Mode

To run Meetling in debug mode, type:

```sh
python -m meetling --debug
```

## Running the Tests

To run all unit tests, type:

```sh
python -m unittest discover -v
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
