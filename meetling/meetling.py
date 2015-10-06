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
from datetime import datetime, timedelta
from redis import StrictRedis
from meetling.lib.jsonredis import JSONRedis, JSONRedisMapping
from meetling.util import randstr, str_or_none

class Meetling:
    """See :ref:`Meetling`.

    .. attribute:: user

       Current :class:`User`. ``None`` means anonymous access.

    .. attribute:: users

       Map of all :class:`User` s.

    .. attribute:: settings

       App :class:`Settings`.

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

        self.user = None
        self.meetings = JSONRedisMapping(self.r, 'meetings')
        self.users = JSONRedisMapping(self.r, 'users')

    @property
    def settings(self):
        return self.r.oget('Settings')

    def update(self):
        """Update the Meetling database.

        If the database is fresh, it will be initialized. If the database is already up-to-date,
        nothing will be done. It is thus safe to call :meth:`update` without knowing if an update is
        necessary or not.
        """
        db_version = self.r.get('version')
        if not db_version:
            settings = Settings(id='Settings', app=self, title='My Meetling', icon=None,
                                favicon=None)
            self.r.oset(settings.id, settings)
            self.r.set('version', 1)

    def authenticate(self, secret):
        """Authenticate an :class:`User` (device) with *secret*.

        The identified user is set as current *user* and returned. If the authentication fails, a
        :exc:`ValueError` (``secret_invalid``) is raised.
        """
        id = self.r.hget('auth_secret_map', secret)
        if not id:
            raise ValueError('secret_invalid')
        self.user = self.users[id.decode()]
        return self.user

    def login(self):
        """See :http:post:`/api/login`.

        The new user is set as current *user*.
        """
        user = User(id='User:' + randstr(), app=self, auth_secret=randstr())
        self.r.oset(user.id, user)
        self.r.rpush('users', user.id)
        self.r.hset('auth_secret_map', user.auth_secret, user.id)
        return self.authenticate(user.auth_secret)

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

    def create_example_meeting(self):
        """See :http:post:`/api/create-example-meeting`."""
        time = (datetime.utcnow() + timedelta(days=7)).replace(hour=12, minute=0, second=0,
                                                               microsecond=0)
        meeting = self.create_meeting(
            'Working group meeting',
            'We meet on {} at the office and discuss important issues.'.format(time.ctime()))
        meeting.create_agenda_item('Round of introductions')
        meeting.create_agenda_item('Lunch poll', 'What will we have for lunch today?')
        meeting.create_agenda_item('Next meeting', 'When and where will our next meeting be?')
        return meeting

    @staticmethod
    def _encode(object):
        try:
            return object.json()
        except AttributeError:
            raise TypeError()

    def _decode(self, json):
        types = {'User': User, 'Settings': Settings, 'Meeting': Meeting, 'AgendaItem': AgendaItem}
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

    def __repr__(self):
        return '<{}>'.format(self.id)

class Editable:
    """See :ref:`Editable`."""

    def edit(self, **attrs):
        """See :http:post:`/api/(object-url)`."""
        self.do_edit(**attrs)
        self.app.r.oset(self.id, self)

    def do_edit(self, **attrs):
        """Subclass API: Perform the edit operation.

        More precisely, validate and then set the given *attrs*. Called by :meth:`edit`, which takes
        care of finally storing the updated object in the database.
        """
        raise NotImplementedError()

class User(Object):
    """See :ref:`User`."""

    def __init__(self, id, app, auth_secret):
        super().__init__(id=id, app=app)
        self.auth_secret = auth_secret

    def json(self, exclude_private=False):
        """See :meth:`Object.json`.

        If *exclude_private* is ``True``, private attributes (*auth_secret*) are excluded.
        """
        json = super().json({'auth_secret': self.auth_secret})
        if exclude_private:
            del json['auth_secret']
        return json

class Settings(Object, Editable):
    """See :ref:`Settings`."""

    def __init__(self, id, app, title, icon, favicon):
        super().__init__(id=id, app=app)
        Editable.__init__(self)
        self.title = title
        self.icon = icon
        self.favicon = favicon

    def do_edit(self, **attrs):
        e = InputError()
        if 'title' in attrs and not str_or_none(attrs['title']):
            e.errors['title'] = 'empty'
        e.trigger()

        if 'title' in attrs:
            self.title = attrs['title']
        if 'icon' in attrs:
            self.icon = str_or_none(attrs['icon'])
        if 'favicon' in attrs:
            self.favicon = str_or_none(attrs['favicon'])

    def json(self):
        return super().json({'title': self.title, 'icon': self.icon, 'favicon': self.favicon})

class Meeting(Object, Editable):
    """See :ref:`Meeting`.

    .. attribute:: items

       Ordered map of :class:`AgendaItem` s on the meeting's agenda.
    """

    def __init__(self, id, app, title, description):
        super().__init__(id=id, app=app)
        Editable.__init__(self)
        self.title = title
        self.description = description
        self.items = JSONRedisMapping(self.app.r, self.id + '.items')

    def do_edit(self, **attrs):
        e = InputError()
        if 'title' in attrs and not str_or_none(attrs['title']):
            e.errors['title'] = 'empty'
        e.trigger()

        if 'title' in attrs:
            self.title = attrs['title']
        if 'description' in attrs:
            self.description = str_or_none(attrs['description'])

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

class AgendaItem(Object, Editable):
    """See :ref:`AgendaItem`."""

    def __init__(self, id, app, title, description):
        super().__init__(id=id, app=app)
        Editable.__init__(self)
        self.title = title
        self.description = description

    def do_edit(self, **attrs):
        e = InputError()
        if 'title' in attrs and not str_or_none(attrs['title']):
            e.errors['title'] = 'empty'
        e.trigger()

        if 'title' in attrs:
            self.title = attrs['title']
        if 'description' in attrs:
            self.description = str_or_none(attrs['description'])

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
