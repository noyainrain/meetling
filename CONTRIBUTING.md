Contributing to Meetling
========================

## How to Contribute

1. For any non-trivial change:
   1. [Create an issue](https://github.com/NoyaInRain/meetling/issues) describing the intended
   change [1]
   2. Receive feedback and adjust your draft accordingly
2. Create a topic branch
3. Code...
4. Run the unit tests and fix possible issues
5. [Create a pull request](https://github.com/NoyaInRain/meetling/pulls)
6. Receive feedback and adjust your contribution accordingly
7. Your contribution is merged \o/

Please make sure to follow the Meetling *Conventions*.

[1] A good description contains:

* If the API or web API is modified, any method signature (including the return value and possible
  errors) and object signature (including properties)
* If the UI is modified, a simple sketch
* If a new dependency is introduced, a short description of the dependency and possible alternatives
  and the reason why it is the best option

## Development Dependencies

For development, the following additional requirements must be set up on your system:

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

## Conventions

* [KISS](https://en.wikipedia.org/wiki/KISS_principle)
* [DRY](https://en.wikipedia.org/wiki/Don%27t_repeat_yourself)
* [Python style guide](https://www.python.org/dev/peps/pep-0008/)
* Consistency: Take a look around and be consistent with what you see
* Public methods/functions should:
  * Validate all input and current state if necessary
  * Have one or more accompanying unit tests (unless the functionality is trivial)
