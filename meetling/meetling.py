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

"""Core parts of Meetling."""

from urllib.parse import ParseResult, urlparse, urljoin
from redis import StrictRedis
from meetling.lib.jsonredis import JSONRedis, JSONRedisMapping
from meetling.util import randstr, str_or_none

class Meetling:
    """See :ref:`Meetling`.

    .. attribute:: meetings

       Map of all :class:`Meeting` s.

    .. attribute:: redis_url

       See ``--redis-url`` command line option.

    .. attribute:: r

       :class:`Redis` database. More precisely a :class:`JSONRedis` instance.
    """

    def __init__(self, redis_url=''):
        e = InputError()
        try:
            components = urlparse(redis_url)
            # Port errors are only triggered on access
            components.port
        except ValueError:
            e.errors['redis_url'] = 'invalid'
        if e.errors:
            raise e

        self.redis_url = redis_url
        components = ParseResult(
            'redis', '{}:{}'.format(components.hostname or 'localhost', components.port or '6379'),
            urljoin('/', components.path or '0'), '', '', '')
        self.r = StrictRedis(components.hostname, components.port, components.path.lstrip('/'))
        self.r = JSONRedis(self.r, self._encode, self._decode)

        self.meetings = JSONRedisMapping(self.r, 'meetings')

    def create_meeting(self, title, description=None):
        """See :http:post:`/api/meetings`."""
        e = InputError()
        if not str_or_none(title):
            e.errors['title'] = 'empty'
        description = str_or_none(description)
        e.trigger()

        meeting = Meeting(id='Meeting:' + randstr(), app=self, title=title, description=description)
        self.r.oset(meeting.id, meeting)
        self.r.rpush('meetings', meeting.id)
        return meeting

    @staticmethod
    def _encode(object):
        try:
            return object.json()
        except AttributeError:
            raise TypeError()

    def _decode(self, json):
        types = {'Meeting': Meeting, 'AgendaItem': AgendaItem}
        try:
            type = json.pop('__type__')
        except KeyError:
            return json
        return types[type](app=self, **json)

class Object:
    """Object in the Meetling universe.

    .. attribute:: id

       Unique ID of the object.

    .. attribute:: app

       Context :class:`Meetling` application.
    """

    def __init__(self, id, app):
        self.id = id
        self.app = app

    def json(self, attrs={}):
        """Return a JSON object representation of the object.

        The name of the object type is included as ``__type__``.
        """
        json = {'__type__': type(self).__name__, 'id': self.id}
        json.update(attrs)
        return json

class Meeting(Object):
    """See :ref:`Meeting`.

    .. attribute:: items

       Ordered map of :class:`AgendaItem` s on the meeting's agenda.
    """

    def __init__(self, id, app, title, description):
        super().__init__(id=id, app=app)
        self.title = title
        self.description = description
        self.items = JSONRedisMapping(self.app.r, self.id + '.items')

    def edit(self, **attrs):
        """See :http:post:`/api/meetings/(id)`."""
        e = InputError()
        if 'title' in attrs and not str_or_none(attrs['title']):
            e.errors['title'] = 'empty'
        e.trigger()

        if 'title' in attrs:
            self.title = attrs['title']
        if 'description' in attrs:
            self.description = str_or_none(attrs['description'])
        self.app.r.oset(self.id, self)

    def create_agenda_item(self, title, description=None):
        """See :http:post:`/api/meetings/(id)/items`."""
        e = InputError()
        if not str_or_none(title):
            e.errors['title'] = 'empty'
        description = str_or_none(description)
        e.trigger()

        item = AgendaItem(id='AgendaItem:' + randstr(), app=self.app, title=title,
                          description=description)
        self.app.r.oset(item.id, item)
        self.app.r.rpush(self.id + '.items', item.id)
        return item

    def json(self):
        return super().json({'title': self.title, 'description': self.description})

class AgendaItem(Object):
    """See :ref:`AgendaItem`."""

    def __init__(self, id, app, title, description):
        super().__init__(id=id, app=app)
        self.title = title
        self.description = description

    def edit(self, **attrs):
        """See :http:post:`/api/meetings/(meeting-id)/items/(item-id)`."""
        e = InputError()
        if 'title' in attrs and not str_or_none(attrs['title']):
            e.errors['title'] = 'empty'
        e.trigger()

        if 'title' in attrs:
            self.title = attrs['title']
        if 'description' in attrs:
            self.description = str_or_none(attrs['description'])
        self.app.r.oset(self.id, self)

    def json(self):
        return super().json({'title': self.title, 'description': self.description})

class InputError(ValueError):
    """See :ref:`InputError`.

    To raise an :exc:`InputError`, apply the following pattern::

       def meow(volume):
           e = InputError()
           if not 0 < volume <= 1:
               e.errors['volume'] = 'out_of_range'
           e.trigger()
           # ...
    """

    def __init__(self):
        super().__init__('input_invalid')
        self.errors = {}

    def trigger(self):
        """Trigger the error, i.e. raise it if any *errors* are present.

        If *errors* is empty, do nothing.
        """
        if self.errors:
            raise self
