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
from datetime import datetime, timedelta
from email.message import EmailMessage
import re
from smtplib import SMTP
from urllib.parse import urlparse

from redis import StrictRedis

from micro.jsonredis import JSONRedis, JSONRedisMapping
from micro.util import check_email, parse_isotime, randstr, str_or_none

class Application:
    """See :ref:`Application`.

    .. attribute:: user

       Current :class:`User`. ``None`` means anonymous access.

    .. attribute:: users

       Map of all :class:`User` s.

    .. attribute:: redis_url

       See ``--redis-url`` command line option.

    .. attribute:: email

       Sender email address to use for outgoing email. Defaults to ``bot@localhost``.

    .. attribute:: smtp_url

       See ``--smtp-url`` command line option.

    .. attribute:: render_email_auth_message

       Hook function of the form *render_email_auth_message(email, auth_request, auth)*, responsible
       for rendering an email message for the authentication request *auth_request*. *email* is the
       email address to authenticate and *auth* is the secret authentication code.

    .. attribute:: r

       :class:`Redis` database. More precisely a :class:`JSONRedis` instance.
    """

    def __init__(self, redis_url='', email='bot@localhost', smtp_url='',
                 render_email_auth_message=None):
        check_email(email)
        try:
            # pylint: disable=pointless-statement; port errors are only triggered on access
            urlparse(smtp_url).port
        except builtins.ValueError:
            raise ValueError('smtp_url_invalid')

        self.redis_url = redis_url
        try:
            self.r = StrictRedis.from_url(self.redis_url)
        except builtins.ValueError:
            raise ValueError('redis_url_invalid')
        self.r = JSONRedis(self.r, self._encode, self._decode)

        self.types = {'User': User, 'Settings': Settings, 'AuthRequest': AuthRequest}
        self.user = None
        self.users = JSONRedisMapping(self.r, 'users')
        self.email = email
        self.smtp_url = smtp_url
        self.render_email_auth_message = render_email_auth_message

        self.stats = None
        self.stats_meta = {'users': self._count_users}

    @property
    def settings(self):
        """App :class:`Settings`."""
        return self.r.oget('Settings')

    def update(self):
        """Update the database.

        If the database is fresh, it will be initialized. If the database is already up-to-date,
        nothing will be done. It is thus safe to call :meth:`update` without knowing if an update is
        necessary or not.
        """
        # Compatibility for databases without micro_version (obsolete since 0.13.0)
        if not self.r.exists('micro_version') and self.r.exists('Settings'):
            self.r.set('micro_version', 0)

        version = self.r.get('micro_version')

        # If fresh, initialize database
        if not version:
            settings = self.create_settings()
            self.r.oset(settings.id, settings)
            self.r.set('micro_version', 3)
            self.do_update()
            return

        version = int(version)
        r = JSONRedis(self.r.r)
        r.caching = False

        if version < 2:
            settings = r.oget('Settings')
            settings['feedback_url'] = None
            r.oset(settings['id'], settings)
            r.set('micro_version', 2)

        if version < 3:
            from collections.abc import Mapping
            from redis.exceptions import ResponseError

            def objectiter():
                for key in r.scan_iter():
                    try:
                        object = r.oget(key)
                    except ResponseError:
                        # TODO: subclass response error to type response error
                        continue
                    if not (isinstance(object, Mapping) and '__type__' in object):
                        continue
                    type = self.types[object['__type__']]
                    yield key, object, type
            #types = [t for self.types if issubclass(t, Object)]
            #for key in r.scan_iter():
            #    try:
            #        object = r.oget(key)
            #    except ResponseError:
            #        # TODO: subclass response error to type
            #        continue
            #    if not isinstance(object, Mapping):
            #        continue

            now = self.now().isoformat() + 'Z'
            for key, object, type in objectiter():
                # everything in db is object, lol :)
                #if issubclass(type, Object):
                object['create_time'] = now
                r.oset(key, object)

            r.set('micro_version', 3)

        self.do_update()

    def do_update(self):
        """Subclass API: Perform the database update.

        May be overridden by subclass. Called by :meth:`update`, which takes care of updating (or
        initializing) micro specific data. The default implementation does nothing.
        """
        pass

    def create_settings(self):
        """Subclass API: Create and return the app :class:`Settings`.

        *id* must be set to ``Settings``.

        Must be overridden by subclass. Called by :meth:`update` when initializing the database.
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
            user = User(id=id, trashed=False, create_time=self.now().isoformat() + 'Z',
                        authors=[id], name='Guest', email=None, auth_secret=randstr(), app=self)
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

    def get_object(self, id, default=KeyError):
        """Get the :class:`Object` given by *id*.

        *default* is the value to return if no object with *id* is found. If it is an
        :exc:`Exception`, it is raised instead.
        """
        object = self.r.oget(id)
        if object is None:
            object = default
        if isinstance(object, Exception):
            raise object
        return object

    def now(self):
        # TODO: some better place?
        return datetime.utcnow()

    def produce_stats(self):
        # two kind of stats
        # absolute numbers (interesting for users, meetings, ...)
        # per-time-unit (interesting for requests, actions, ... - where the absolute number is nicht
        #                aussagekraeftig, high frequency, better to express change)
        #  ^ for this we must compute the average over the time span
        #    count(objects, start, end) / ((end - start) * timeunits) eg
        #    count(requests, monthago, now) / ((now - montago) * 60) to compute the
        #    requests/minute on average for the last month. requests can be stored as a list or a
        #    day histogram
        # for per time unit stuff, the UI must show last month/week/.. instead of one month/week/..
        # ago
        # also for per time unit stuff, the peak/maximum value might be interesting also. the
        # histogram width must be at least the time unit for that (e.g. minute-histogram for
        # requests/minute)

        # TODO: make for all registered stats
        #stats = {
        #    'users': count_users,
        #    'meetings': count_meetings,
        #    'agenda_items': count_agenda_items,
        #    'foo': (COUNT, count_foo), # function gets list of times
        #    'requests': (RATE, count_requests, 60), # function gets list of ranges (start, end)
        #}

        from itertools import chain

        now = self.now()
        deltas = [('now', timedelta()), ('1w', timedelta(days=7)), ('1m', timedelta(days=30)),
                  ('1y', timedelta(days=360))]
        times = ([now, now - timedelta(days=1)] +
                 list(chain.from_iterable((now - d[1], now - d[1] * 2) for d in deltas[1:])))
        #print(times)

        data = {}
        for topic, count in self.stats_meta.items():
            counts = count(times)
            #stats = [tuple(counts[i:i + 2]) for i in range(0, len(counts), 2)]
            #stats = [(v[0], v[1] - v[0]) for v in stats] # rate of change
            xstats = [(counts[i], counts[i] - counts[i + 1]) for i in range(0, len(counts), 2)]
            data[topic] = {d[0]: v for d, v in zip(deltas, xstats)}

        #print(stats)
        self.stats = Stats(id='Stats', trashed=False, create_time=now.isoformat() + 'Z', data=data,
                           app=self)

    def sample(self):
        """TODO."""
        now = self.now()
        reset_now = self.now
        self.now = lambda: now - timedelta(days=361)
        staff_member = self.login()
        staff_member.edit(name='Ceiling')
        self.login()
        self.now = lambda: now - timedelta(days=31)
        self.login()
        self.now = lambda: now - timedelta(days=15)
        self.login()
        self.now = lambda: now - timedelta(hours=12)
        self.login()
        self.now = reset_now

        user = self.login()
        user.edit(name='Happy')
        # Create an AuthRequest
        user.set_email('happy@example.org')

        self.do_sample()

        self.produce_stats()

    def do_sample(self):
        """TODO.
        Subclass API:

        the currently logged in user is a std user 'Happy'.
        """

    def _count_users(self, times):
        return [sum(1 for u in self.users.values() if u.create_time <= t) for t in times]

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

    def __init__(self, id, trashed, create_time, app):
        self.id = id
        self.trashed = trashed
        self.create_time = parse_isotime(create_time)
        self.app = app

    def json(self, restricted=False):
        """Return a JSON object representation of the object.

        The name of the object type is included as ``__type__``.

        By default, all attributes are included. If *restricted* is ``True``, a restricted view of
        the object is returned, i.e. attributes that should not be available to the current
        :attr:`Meetling.user` are excluded.

        Subclass API: May be overridden by subclass. The default implementation returns the
        attributes of :class:`Object`. *restricted* is ignored.
        """
        # pylint: disable=unused-argument; restricted is part of the subclass API
        return {
            '__type__': type(self).__name__,
            'id': self.id,
            'trashed': self.trashed,
            'create_time': self.create_time.isoformat() + 'Z'
        }

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

    def __init__(self, id, trashed, create_time, authors, name, email, auth_secret, app):
        super().__init__(id=id, trashed=trashed, create_time=create_time, app=app)
        Editable.__init__(self, authors=authors)
        self.name = name
        self.email = email
        self.auth_secret = auth_secret

    def store_email(self, email):
        """Update the user's *email* address.

        If *email* is already associated with another user, a :exc:`ValueError`
        (``email_duplicate``) is raised.
        """
        check_email(email)
        id = self.app.r.hget('user_email_map', email)
        if id and id.decode() != self.id:
            raise ValueError('email_duplicate')

        if self.email:
            self.app.r.hdel('user_email_map', self.email)
        self.email = email
        self.app.r.oset(self.id, self)
        self.app.r.hset('user_email_map', self.email, self.id)

    def set_email(self, email):
        """See :http:post:`/api/users/(id)/set-email`."""
        if self.app.user != self:
            raise PermissionError()
        check_email(email)

        code = randstr()
        auth_request = AuthRequest(
            id='AuthRequest:' + randstr(), trashed=False,
            create_time=self.app.now().isoformat() + 'Z', email=email, code=code, app=self.app)
        self.app.r.oset(auth_request.id, auth_request)
        self.app.r.expire(auth_request.id, 10 * 60)
        if self.app.render_email_auth_message:
            self._send_email(email, self.app.render_email_auth_message(email, auth_request, code))
        return auth_request

    def finish_set_email(self, auth_request, auth):
        """See :http:post:`/api/users/(id)/finish-set-email`."""
        # pylint: disable=protected-access; auth_request is a friend
        if self.app.user != self:
            raise PermissionError()
        if auth != auth_request._code:
            raise ValueError('auth_invalid')

        self.app.r.delete(auth_request.id)
        self.store_email(auth_request._email)

    def remove_email(self):
        """See :http:post:`/api/users/(id)/remove-email`."""
        if self.app.user != self:
            raise PermissionError()
        if not self.email:
            raise ValueError('user_no_email')

        self.app.r.hdel('user_email_map', self.email)
        self.email = None
        self.app.r.oset(self.id, self)

    def send_email(self, msg):
        """Send an email message to the user.

        *msg* is the message string of the following form: It starts with a line containing the
        subject prefixed with ``Subject: ``, followed by a blank line, followed by the body.

        If the user's ::attr:`email` is not set, a :exception:`ValueError` (``user_no_email``) is
        raised. If communication with the SMTP server fails, an :ref:`EmailError` is raised.
        """
        if not self.email:
            raise ValueError('user_no_email')
        self._send_email(self.email, msg)

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
        json = super().json(restricted=restricted)
        json.update({'name': self.name, 'email': self.email, 'auth_secret': self.auth_secret})
        json.update(Editable.json(self, restricted=restricted, include_users=include_users))
        if restricted and not self.app.user == self:
            del json['email']
            del json['auth_secret']
        return json

    def _send_email(self, to, msg):
        match = re.fullmatch(r'Subject: ([^\n]+)\n\n(.+)', msg, re.DOTALL)
        if not match:
            raise ValueError('msg_invalid')

        msg = EmailMessage()
        msg['To'] = to
        msg['From'] = self.app.email
        msg['Subject'] = match.group(1)
        msg.set_content(match.group(2))

        components = urlparse(self.app.smtp_url)
        host = components.hostname or 'localhost'
        port = components.port or 25
        try:
            with SMTP(host=host, port=port) as smtp:
                smtp.send_message(msg)
        except OSError:
            raise EmailError()

class Settings(Object, Editable):
    """See :ref:`Settings`."""

    def __init__(self, id, trashed, create_time, authors, title, icon, favicon, feedback_url, staff,
                 app):
        super().__init__(id=id, trashed=trashed, create_time=create_time, app=app)
        Editable.__init__(self, authors=authors)
        self.title = title
        self.icon = icon
        self.favicon = favicon
        self.feedback_url = feedback_url
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
        if 'feedback_url' in attrs:
            self.feedback_url = str_or_none(attrs['feedback_url'])

    def json(self, restricted=False, include_users=False):
        json = super().json()
        json.update({
            'title': self.title,
            'icon': self.icon,
            'favicon': self.favicon,
            'feedback_url': self.feedback_url,
            'staff': self._staff
        })
        json.update(Editable.json(self, restricted=restricted, include_users=include_users))
        if include_users:
            json['staff'] = [u.json(restricted=restricted) for u in self.staff]
        return json

class Stats(Object):
    """TODO."""

    def __init__(self, id, trashed, create_time, data, app):
        super().__init__(id=id, trashed=trashed, create_time=create_time, app=app)
        self.data = data

    def json(self, restricted=False):
        json = super().json(restricted=restricted)
        json['data'] = self.data
        return json

class AuthRequest(Object):
    """See :ref:`AuthRequest`."""

    def __init__(self, id, trashed, create_time, app, email, code):
        super().__init__(id=id, trashed=trashed, create_time=create_time, app=app)
        self._email = email
        self._code = code

    def json(self, restricted=False):
        json = super().json(restricted=restricted)
        json.update({'email': self._email, 'code': self._code})
        if restricted:
            del json['email']
            del json['code']
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

class EmailError(Exception):
    """Raised if communication with the SMTP server fails."""
    pass
