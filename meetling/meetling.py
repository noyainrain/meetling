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
from meetling.util import randstr, str_or_none, parse_isotime

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
            settings = Settings(id='Settings', app=self, authors=[], title='My Meetling', icon=None,
                                favicon=None, staff=[])
            self.r.oset(settings.id, settings)
            self.r.set('version', 2)
            return

        db_version = int(db_version)
        # JSONRedis without en-/decoding and caching
        r = JSONRedis(self.r.r)
        r.caching = False

        if db_version < 2:
            users = r.omget(r.lrange('users', 0, -1))
            for user in users:
                user['name'] = 'Guest'
                user['authors'] = [user['id']]
            r.omset({u['id']: u for u in users})
            r.set('version', 2)

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
        id = 'User:' + randstr()
        user = User(id=id, app=self, authors=[id], name='Guest', auth_secret=randstr())
        self.r.oset(user.id, user)
        self.r.rpush('users', user.id)
        self.r.hset('auth_secret_map', user.auth_secret, user.id)

        # Promote first user to staff
        if len(self.users) == 1:
            settings = self.settings
            settings._staff = [user.id]
            self.r.oset(settings.id, settings)

        return self.authenticate(user.auth_secret)

    def create_meeting(self, title, time=None, location=None, description=None):
        """See :http:post:`/api/meetings`."""
        if not self.user:
            raise PermissionError()

        e = InputError()
        if not str_or_none(title):
            e.errors['title'] = 'empty'
        e.trigger()

        meeting = Meeting(
            id='Meeting:' + randstr(), app=self, authors=[self.user.id], title=title, time=time,
            location=str_or_none(location), description=str_or_none(description))
        self.r.oset(meeting.id, meeting)
        self.r.rpush('meetings', meeting.id)
        return meeting

    def create_example_meeting(self):
        """See :http:post:`/api/create-example-meeting`."""
        if not self.user:
            raise PermissionError()

        time = (datetime.utcnow() + timedelta(days=7)).replace(hour=12, minute=0, second=0,
                                                               microsecond=0)
        meeting = self.create_meeting('Working group meeting', time, 'At the office',
                                      'We meet and discuss important issues.')
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
        type = types[type]

        if type is Meeting and json['time']:
            json['time'] = parse_isotime(json['time'])

        return type(app=self, **json)

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
    """See :ref:`Editable`.

    The :meth:`Object.json` method of editable objects accepts an additional argument
    *include_users*. If it is ``True``, :class:`User` s are included as JSON objects (instead of
    IDs).
    """

    def __init__(self, authors):
        self._authors = authors

    @property
    def authors(self):
        return self.app.r.omget(self._authors)

    def edit(self, **attrs):
        """See :http:post:`/api/(object-url)`."""
        if not self.app.user:
            raise PermissionError()

        self.do_edit(**attrs)
        if not self.app.user.id in self._authors:
            self._authors.append(self.app.user.id)
        self.app.r.oset(self.id, self)

    def do_edit(self, **attrs):
        """Subclass API: Perform the edit operation.

        More precisely, validate and then set the given *attrs*. Called by :meth:`edit`, which takes
        care of basic permission checking, managing *authors* and storing the updated object in the
        database.
        """
        raise NotImplementedError()

    def json(self, include_users=False):
        """Subclass API: Return a JSON object representation of the editable part of the object."""
        json = {'authors': self._authors}
        if include_users:
            json['authors'] = [a.json(exclude_private=True) for a in self.authors]
        return json

class User(Object, Editable):
    """See :ref:`User`."""

    def __init__(self, id, app, authors, name, auth_secret):
        super().__init__(id=id, app=app)
        Editable.__init__(self, authors=authors)
        self.name = name
        self.auth_secret = auth_secret

    def do_edit(self, **attrs):
        if self.app.user != self:
            raise PermissionError()

        e = InputError()
        if 'name' in attrs and not str_or_none(attrs['name']):
            e.errors['name'] = 'empty'
        e.trigger()

        if 'name' in attrs:
            self.name = attrs['name']

    def json(self, include_users=False, exclude_private=False):
        """See :meth:`Object.json`.

        If *exclude_private* is ``True``, private attributes (*auth_secret*) are excluded.
        """
        json = super().json({'name': self.name, 'auth_secret': self.auth_secret})
        json.update(Editable.json(self, include_users))
        if exclude_private:
            del json['auth_secret']
        return json

class Settings(Object, Editable):
    """See :ref:`Settings`."""

    def __init__(self, id, app, authors, title, icon, favicon, staff):
        super().__init__(id=id, app=app)
        Editable.__init__(self, authors=authors)
        self.title = title
        self.icon = icon
        self.favicon = favicon
        self._staff = staff

    @property
    def staff(self):
        return self.app.r.omget(self._staff)

    def do_edit(self, **attrs):
        if not self.app.user.id in self._staff:
            raise PermissionError()

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

    def json(self, include_users=False):
        json = super().json({
            'title': self.title,
            'icon': self.icon,
            'favicon': self.favicon,
            'staff': self._staff
        })
        json.update(Editable.json(self, include_users))
        if include_users:
            json['staff'] = [u.json(exclude_private=True) for u in self.staff]
        return json

class Meeting(Object, Editable):
    """See :ref:`Meeting`.

    .. attribute:: items

       Ordered map of :class:`AgendaItem` s on the meeting's agenda.
    """

    def __init__(self, id, app, authors, title, time, location, description):
        super().__init__(id=id, app=app)
        Editable.__init__(self, authors=authors)
        self.title = title
        self.time = time
        self.location = location
        self.description = description
        self.items = JSONRedisMapping(self.app.r, self.id + '.items')

    def do_edit(self, **attrs):
        e = InputError()
        if 'title' in attrs and not str_or_none(attrs['title']):
            e.errors['title'] = 'empty'
        e.trigger()

        if 'title' in attrs:
            self.title = attrs['title']
        if 'time' in attrs:
            self.time = attrs['time']
        if 'location' in attrs:
            self.location = str_or_none(attrs['location'])
        if 'description' in attrs:
            self.description = str_or_none(attrs['description'])

    def create_agenda_item(self, title, description=None):
        """See :http:post:`/api/meetings/(id)/items`."""
        if not self.app.user:
            raise PermissionError()

        e = InputError()
        if not str_or_none(title):
            e.errors['title'] = 'empty'
        description = str_or_none(description)
        e.trigger()

        item = AgendaItem(id='AgendaItem:' + randstr(), app=self.app, authors=[self.app.user.id],
                          title=title, description=description)
        self.app.r.oset(item.id, item)
        self.app.r.rpush(self.id + '.items', item.id)
        return item

    def json(self, include_users=False):
        json = super().json({
            'title': self.title,
            'time': self.time.isoformat() + 'Z' if self.time else None,
            'location': self.location,
            'description': self.description
        })
        json.update(Editable.json(self, include_users))
        return json

class AgendaItem(Object, Editable):
    """See :ref:`AgendaItem`."""

    def __init__(self, id, app, authors, title, description):
        super().__init__(id=id, app=app)
        Editable.__init__(self, authors=authors)
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

    def json(self, include_users=False):
        json = super().json({'title': self.title, 'description': self.description})
        json.update(Editable.json(self, include_users))
        return json

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

    def __init__(self, errors={}):
        super().__init__('input_invalid')
        self.errors = dict(errors)

    def trigger(self):
        """Trigger the error, i.e. raise it if any *errors* are present.

        If *errors* is empty, do nothing.
        """
        if self.errors:
            raise self

class PermissionError(Exception):
    """See :ref:`PermissionError`."""
    pass
