# Contributing to Meetling

## How to contribute

1. For any non-trivial contribution:
   1. [Create an issue](https://github.com/NoyaInRain/meetling/issues) describing the intended
      change [1]
   2. A team member reviews your draft. Make the requested changes, if any.
2. Create a topic branch
3. Code...
4. [Create a pull request](https://github.com/NoyaInRain/meetling/pulls)
5. Travis CI runs the code quality checks. Fix the reported issues, if any.
6. A team member reviews your contribution. Make the requested changes, if any.
7. A team member merges your contribution \o/

[1] A good description contains:

* If the API or web API is modified, any method signature (including the return value and possible
  errors) and object signature (including properties)
* If the UI is modified, a simple sketch
* If a new dependency is introduced, a short description of the dependency and possible alternatives
  and the reason why it is the best option

## Installing development dependencies

To install the development dependencies for Meetling, type:

```sh
make deps-dev
```

## Running Meetling in debug mode

To run Meetling in debug mode, type:

```sh
python3 -m meetling --debug
```

## Running the unit tests

To run all unit tests, type:

```sh
make
```

## Development utilities

The Makefile that comes with Meetling provides additional utilities for different development tasks.
To get an overview, type:

```sh
make help
```
