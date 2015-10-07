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

"""Application for collaboratively preparing meetings.

Most of the functionality is documented in :doc:`webapi`; please have a look at it. The focus of
this documentation is on the differences and additions to the Web API.

Meetling is based on Redis and thus any method may raise a :exc:`RedisError` if there is a problem
communicating with the Redis server.
"""

import os
from meetling.meetling import Meetling, Object, Editable, Meeting, AgendaItem, InputError

_RES_PATH = os.path.join(os.path.dirname(__file__), 'res')
