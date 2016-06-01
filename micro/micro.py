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

"""Core parts of micro."""

import builtins
from urllib.parse import ParseResult, urlparse, urljoin

from redis import StrictRedis

from micro.jsonredis import JSONRedis, JSONRedisMapping
from micro.util import randstr, str_or_none

class Application:
    """See :ref:`Application`.

    .. attribute:: user

       Current :class:`User`. ``None`` means anonymous access.

    .. attribute:: users

       Map of all :class:`User` s.

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

        self.types = {'User': User, 'Settings': Settings}
        self.user = None
        self.users = JSONRedisMapping(self.r, 'users')

    @property
    def settings(self):
        """App :class:`Settings`."""
        return self.r.oget('Settings')

    def update(self):
        """Update the database.

        If the database is fresh, it will be initialized. If the database is already up-to-date,
        nothing will be done. It is thus safe to call :meth:`update` without knowing if an update is
        necessary or not.

        Subclass API: Must be implemented by subclass.
        """
        raise NotImplementedError()

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

    @staticmethod
    def _encode(object):
        try:
            return object.json()
        except AttributeError:
            raise TypeError()

    def _decode(self, json):
        try:
            type = json.pop('__type__')
        except KeyError:
            return json
        type = self.types[type]
        return type(app=self, **json)

class Object:
    """See :ref:`Object`.

    .. attribute:: app

       Context :class:`Application`.
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
