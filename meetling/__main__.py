# Meetling
# Copyright (C) 2015 Meetling contributors
#
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU
# General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without
# even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program. If not,
# see <http://www.gnu.org/licenses/>.

"""Meetling script."""

import sys
import argparse
from argparse import ArgumentParser
from meetling.server import MeetlingServer

def main(args):
    """Run Meetling.

    *args* is the list of command line arguments. See ``python3 -m meetling -h``.
    """
    parser = ArgumentParser(argument_default=argparse.SUPPRESS)
    parser.add_argument(
        '--port',
        help='Port number the server listens on for incoming connections. Defaults to 8080.')
    parser.add_argument(
        '--host',
        help='TODO host name the server listens on for incoming connections. Defaults to 0.0.0.0, which is special for listening to any host name')
    parser.add_argument('--debug', action='store_true', help='Debug mode.')
    parser.add_argument(
        '--redis-url',
        help='URL of the Redis database. Only host, port and path (representing the database index) are considered, all other components are ignored. Defaults to redis://localhost:6379/0.')
    args = parser.parse_args(args[1:])

    MeetlingServer(**vars(args)).run()
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
