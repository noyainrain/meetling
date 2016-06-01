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

"""Various utilities."""

import re
import string
import random
from datetime import datetime

def str_or_none(str):
    """Return *str* unmodified if it has content, otherwise return ``None``.

    A string is considered to have content if it contains at least one non-whitespace character.
    """
    return str if str and str.strip() else None

def randstr(length=16, charset=string.ascii_lowercase):
    """Generate a random string.

    The string will have the given *length* and consist of characters from *charset*.
    """
    return ''.join(random.choice(charset) for i in range(length))

def parse_isotime(isotime):
    """Parse an ISO 8601 time string into a naive :class:`datetime.datetime`.

    Note that this rudimentary parser makes bold assumptions about the format: The first six
    components are always interpreted as year, month, day and optionally hour, minute and second.
    Everything else, i.e. microsecond and time zone information, is ignored.
    """
    try:
        return datetime(*(int(t) for t in re.split(r'\D', isotime)[:6]))
    except (TypeError, ValueError):
        raise ValueError('isotime_bad_format')
