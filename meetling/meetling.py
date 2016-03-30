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

import builtins
from datetime import datetime, timedelta
from itertools import chain
from urllib.parse import ParseResult, urlparse, urljoin

from redis import StrictRedis

from meetling.lib.jsonredis import JSONRedis, JSONRedisMapping
from meetling.util import randstr, str_or_none, parse_isotime

class Meetling:
    """See :ref:`Meetling`.

    .. attribute:: user

       Current :class:`User`. ``None`` means anonymous access.

    .. attribute:: users

       Map of all :class:`User` s.

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
            # pylint: disable=pointless-statement; port errors are only triggered on access
            components.port
        except builtins.ValueError:
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
        """App :class:`Settings`."""
        return self.r.oget('Settings')

    def update(self):
        """Update the Meetling database.

        If the database is fresh, it will be initialized. If the database is already up-to-date,
        nothing will be done. It is thus safe to call :meth:`update` without knowing if an update is
        necessary or not.
        """
        db_version = self.r.get('version')
        if not db_version:
            settings = Settings(id='Settings', trashed=False, app=self, authors=[],
                                title='My Meetling', icon=None, favicon=None, staff=[])
            self.r.oset(settings.id, settings)
            self.r.set('version', 4)
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

        if db_version < 3:
            meetings = r.omget(r.lrange('meetings', 0, -1))
            for meeting in meetings:
                meeting['time'] = None
                meeting['location'] = None

                items = r.omget(r.lrange(meeting['id'] + '.items', 0, -1))
                for item in items:
                    item['duration'] = None
                r.omset({i['id']: i for i in items})
            r.omset({m['id']: m for m in meetings})
            r.set('version', 3)

        if db_version < 4:
            meeting_ids = r.lrange('meetings', 0, -1)
            objects = r.omget(chain(
                ['Settings'],
                r.lrange('users', 0, -1),
                meeting_ids,
                chain.from_iterable(r.lrange(i + b'.items', 0, -1) for i in meeting_ids)
            ))
            for object in objects:
                object['trashed'] = False
            r.omset({o['id']: o for o in objects})
            r.set('version', 4)

    def authenticate(self, secret):
        """Authenticate an :class:`User` (device) with *secret*.

        The identified user is set as current *user* and returned. If the authentication fails, an
        :exc:`AuthenticationError` is raised.
        """
        id = self.r.hget('auth_secret_map', secret)
        if not id:
            raise AuthenticationError()
        self.user = self.users[id.decode()]
        return self.user

    def login(self, code=None):
        """See :http:post:`/api/login`.

        The logged-in user is set as current *user*.
        """
        if code:
            id = self.r.hget('auth_secret_map', code)
            if not id:
                raise ValueError('code_invalid')
            user = self.users[id.decode()]

        else:
            id = 'User:' + randstr()
            user = User(id=id, trashed=False, app=self, authors=[id], name='Guest',
                        auth_secret=randstr())
            self.r.oset(user.id, user)
            self.r.rpush('users', user.id)
            self.r.hset('auth_secret_map', user.auth_secret, user.id)

            # Promote first user to staff
            if len(self.users) == 1:
                settings = self.settings
                # pylint: disable=protected-access; Settings is a friend
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
            id='Meeting:' + randstr(), trashed=False, app=self, authors=[self.user.id], title=title,
            time=time, location=str_or_none(location), description=str_or_none(description))
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
        meeting.create_agenda_item('Lunch poll', duration=30,
                                   description='What will we have for lunch today?')
        meeting.create_agenda_item('Next meeting', duration=5,
                                   description='When and where will our next meeting be?')
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
    """See :ref:`Object`.

    .. attribute:: app

       Context :class:`Meetling` application.
    """

    def __init__(self, id, trashed, app):
        self.id = id
        self.trashed = trashed
        self.app = app

    def json(self, restricted=False, attrs={}):
        """Return a JSON object representation of the object.

        The name of the object type is included as ``__type__``.

        By default, all attributes are included. If *restricted* is ``True``, a restricted view of
        the object is returned, i.e. attributes that should not be available to the current
        :attr:`Meetling.user` are excluded.

        Subclass API: May be overridden by subclass. The default implementation returns the
        attributes of :class:`Object`. *restricted* is ignored.
        """
        # pylint: disable=unused-argument; restricted is part of the subclass API
        json = {'__type__': type(self).__name__, 'id': self.id, 'trashed': self.trashed}
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
    # pylint: disable=no-member; mixin

    def __init__(self, authors):
        self._authors = authors

    @property
    def authors(self):
        # pylint: disable=missing-docstring; already documented
        return self.app.r.omget(self._authors)

    def edit(self, **attrs):
        """See :http:post:`/api/(object-url)`."""
        if not self.app.user:
            raise PermissionError()

        if self.trashed:
            raise ValueError('object_trashed')

        self.do_edit(**attrs)
        if not self.app.user.id in self._authors:
            self._authors.append(self.app.user.id)
        self.app.r.oset(self.id, self)

    def do_edit(self, **attrs):
        """Subclass API: Perform the edit operation.

        More precisely, validate and then set the given *attrs*.

        Must be overridden by host. Called by :meth:`edit`, which takes care of basic permission
        checking, managing *authors* and storing the updated object in the database.
        """
        raise NotImplementedError()

    def json(self, restricted=False, include_users=False):
        """Subclass API: Return a JSON object representation of the editable part of the object."""
        json = {'authors': self._authors}
        if include_users:
            json['authors'] = [a.json(restricted=restricted) for a in self.authors]
        return json

class User(Object, Editable):
    """See :ref:`User`."""

    def __init__(self, id, trashed, app, authors, name, auth_secret):
        super().__init__(id=id, trashed=trashed, app=app)
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

    def json(self, restricted=False, include_users=False):
        """See :meth:`Object.json`."""
        # pylint: disable=arguments-differ; extended signature
        json = super().json(attrs={'name': self.name, 'auth_secret': self.auth_secret})
        json.update(Editable.json(self, restricted=restricted, include_users=include_users))
        if restricted and not self.app.user == self:
            del json['auth_secret']
        return json

class Settings(Object, Editable):
    """See :ref:`Settings`."""

    def __init__(self, id, trashed, app, authors, title, icon, favicon, staff):
        super().__init__(id=id, trashed=trashed, app=app)
        Editable.__init__(self, authors=authors)
        self.title = title
        self.icon = icon
        self.favicon = favicon
        self._staff = staff

    @property
    def staff(self):
        # pylint: disable=missing-docstring; already documented
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

    def json(self, restricted=False, include_users=False):
        json = super().json(attrs={
            'title': self.title,
            'icon': self.icon,
            'favicon': self.favicon,
            'staff': self._staff
        })
        json.update(Editable.json(self, restricted=restricted, include_users=include_users))
        if include_users:
            json['staff'] = [u.json(restricted=restricted) for u in self.staff]
        return json

class Meeting(Object, Editable):
    """See :ref:`Meeting`.

    .. attribute:: items

       Ordered map of :class:`AgendaItem` s on the meeting's agenda.

    .. attribute:: trashed_items

       Ordered map of trashed (deleted) :class:`AgendaItem` s.
    """

    def __init__(self, id, trashed, app, authors, title, time, location, description):
        super().__init__(id=id, trashed=trashed, app=app)
        Editable.__init__(self, authors=authors)
        self.title = title
        self.time = time
        self.location = location
        self.description = description

        self._items_key = self.id + '.items'
        self._trashed_items_key = self.id + '.trashed_items'
        self.items = JSONRedisMapping(self.app.r, self._items_key)
        self.trashed_items = JSONRedisMapping(self.app.r, self._trashed_items_key)

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

    def create_agenda_item(self, title, duration=None, description=None):
        """See :http:post:`/api/meetings/(id)/items`."""
        if not self.app.user:
            raise PermissionError()

        e = InputError()
        if str_or_none(title) is None:
            e.errors['title'] = 'empty'
        if duration is not None and duration <= 0:
            e.errors['duration'] = 'not_positive'
        description = str_or_none(description)
        e.trigger()

        item = AgendaItem(
            id='AgendaItem:' + randstr(), trashed=False, app=self.app, authors=[self.app.user.id],
            title=title, duration=duration, description=description)
        self.app.r.oset(item.id, item)
        self.app.r.rpush(self._items_key, item.id)
        return item

    def trash_agenda_item(self, item):
        """See :http:post:`/api/meetings/(id)/trash-agenda-item`."""
        if not self.app.r.lrem(self._items_key, 1, item.id):
            raise ValueError('item_not_found')
        self.app.r.rpush(self._trashed_items_key, item.id)
        item.trashed = True
        self.app.r.oset(item.id, item)

    def restore_agenda_item(self, item):
        """See :http:post:`/api/meetings/(id)/restore-agenda-item`."""
        if not self.app.r.lrem(self._trashed_items_key, 1, item.id):
            raise ValueError('item_not_found')
        self.app.r.rpush(self._items_key, item.id)
        item.trashed = False
        self.app.r.oset(item.id, item)

    def json(self, restricted=False, include_users=False, include_items=False):
        """See :meth:`Object.json`.

        If *include_items* is ``True``, *items* and *trashed_items* are included.
        """
        # pylint: disable=arguments-differ; extended signature
        json = super().json(attrs={
            'title': self.title,
            'time': self.time.isoformat() + 'Z' if self.time else None,
            'location': self.location,
            'description': self.description
        })
        json.update(Editable.json(self, restricted=restricted, include_users=include_users))
        if include_items:
            json['items'] = [i.json(restricted=restricted, include_users=include_users)
                             for i in self.items.values()]
            json['trashed_items'] = [i.json(restricted=restricted, include_users=include_users)
                                     for i in self.trashed_items.values()]
        return json

class AgendaItem(Object, Editable):
    """See :ref:`AgendaItem`."""

    def __init__(self, id, trashed, app, authors, title, duration, description):
        super().__init__(id=id, trashed=trashed, app=app)
        Editable.__init__(self, authors=authors)
        self.title = title
        self.duration = duration
        self.description = description

    def do_edit(self, **attrs):
        e = InputError()
        if 'title' in attrs and str_or_none(attrs['title']) is None:
            e.errors['title'] = 'empty'
        if attrs.get('duration') is not None and attrs['duration'] <= 0:
            e.errors['duration'] = 'not_positive'
        e.trigger()

        if 'title' in attrs:
            self.title = attrs['title']
        if 'duration' in attrs:
            self.duration = attrs['duration']
        if 'description' in attrs:
            self.description = str_or_none(attrs['description'])

    def json(self, restricted=False, include_users=False):
        json = super().json(attrs={
            'title': self.title,
            'duration': self.duration,
            'description': self.description
        })
        json.update(Editable.json(self, restricted=restricted, include_users=include_users))
        return json

class ValueError(builtins.ValueError):
    """See :ref:`ValueError`.

    The first item of *args* is also available as *code*.
    """

    @property
    def code(self):
        # pylint: disable=missing-docstring; already documented
        return self.args[0] if self.args else None

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

class AuthenticationError(Exception):
    """See :ref:`AuthenticationError`."""
    pass

class PermissionError(Exception):
    """See :ref:`PermissionError`."""
    pass
