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

import argparse
from argparse import ArgumentParser
import logging
from logging import StreamHandler, getLogger
import sys

from tornado.log import LogFormatter

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
        '--url',
        help='Public URL of the server. Defaults to http://localhost with the port option value.')
    parser.add_argument('--debug', action='store_true', help='Debug mode.')
    parser.add_argument(
        '--redis-url',
        help='URL of the Redis database. Only host, port and path (representing the database index) are considered, which default to localhost, 6379 and 0 respectively.')
    parser.add_argument(
        '--smtp-url',
        help='URL of the SMTP server to use for outgoing email. Only host and port are considered, which default to localhost and 25 respectively.')
    args = parser.parse_args(args[1:])

    logger = getLogger()
    handler = StreamHandler()
    handler.setFormatter(LogFormatter())
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    if 'debug' not in args:
        getLogger('tornado.access').setLevel(logging.ERROR)

    MeetlingServer(**vars(args)).run()
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
