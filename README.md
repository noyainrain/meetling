# Meetling

Web app for collaboratively preparing meetings.

![Icon](https://raw.githubusercontent.com/NoyaInRain/meetling/master/meetling/res/static/images/favicon.png)

You can give it a try at [meetling.org](https://meetling.org/).

## Requirements

The following software is required and must be set up on your system:

* Python >= 3.5
* Node.js >= 8.0
* Redis >= 2.8

Support for Python 3.4 and Node.js 0.10 is deprecated since 0.16.4. Support for Node.js 5.0 is
deprecated since 0.18.0.

Meetling should work on any [POSIX](https://en.wikipedia.org/wiki/POSIX) system.

## Installing dependencies

To install the dependencies for Meetling, type:

```sh
make deps
```

## Running Meetling

To run Meetling, type:

```sh
python3 -m meetling
```

## Browser support

Meetling supports the latest version of popular browsers (i.e. Chrome, Edge, Firefox and Safari; see
http://caniuse.com/ ).

## Deprecation policy

Features marked as deprecated are removed after a period of six months.

## Contributors

* Sven James &lt;sven.jms AT gmail.com>

Copyright (C) 2017 Meetling contributors
