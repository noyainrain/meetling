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

# pylint: disable=arguments-differ; Tornado handler arguments are defined by URLs

"""Meetling server."""

from collections import Mapping
import http.client
import json
import logging
import os

from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.web import Application, RequestHandler, HTTPError

import meetling
from meetling import Meetling
from meetling.util import str_or_none, parse_isotime

_CLIENT_ERROR_LOG_TEMPLATE = """\
Client error occurred
%s%s
Stack:
%s
URL: %s
User: %s (%s)
Device info: %s"""

_LOGGER = logging.getLogger(__name__)

class MeetlingServer(HTTPServer):
    """Meetling server.

    .. attribute:: app

       Underlying :class:`meetling.Meetling` application.

    .. attribute:: port

       See ``--port`` command line option.

    .. attribute:: debug

       See ``--debug`` command line option.

    Additional *args* are passed to the :class:`meetling.Meetling` constructor and any errors raised
    by it are passed through.
    """

    def __init__(self, port=8080, debug=False, **args):
        handlers = [
            # UI
            (r'/log-client-error$', _LogClientErrorEndpoint),
            (r'/replace-auth$', _ReplaceAuthEndpoint),
            (r'/(?!api/).*$', _UI),
            # API
            (r'/api/login$', _LoginEndpoint),
            (r'/api/meetings$', _MeetingsEndpoint),
            (r'/api/create-example-meeting$', _CreateExampleMeetingEndpoint),
            (r'/api/users/([^/]+)$', _UserEndpoint),
            (r'/api/settings$', _SettingsEndpoint),
            (r'/api/meetings/([^/]+)$', _MeetingEndpoint),
            (r'/api/meetings/([^/]+)/items(/trashed)?$', _MeetingItemsEndpoint),
            (r'/api/meetings/([^/]+)/trash-agenda-item$', _MeetingTrashAgendaItemEndpoint),
            (r'/api/meetings/([^/]+)/restore-agenda-item$', _MeetingRestoreAgendaItemEndpoint),
            (r'/api/meetings/([^/]+)/move-agenda-item$', _MeetingMoveAgendaItemEndpoint),
            (r'/api/meetings/([^/]+)/items/([^/]+)$', _AgendaItemEndpoint)
        ]
        # pylint: disable=protected-access; meetling is a friend
        application = Application(
            handlers, template_path=os.path.join(meetling._RES_PATH, 'templates'),
            static_path=os.path.join(meetling._RES_PATH, 'static'), debug=debug, server=self)
        super().__init__(application)

        self.port = port
        self.debug = debug
        self.app = Meetling(**args)

    def run(self):
        """Run the server."""
        self.app.update()
        self.listen(self.port)
        IOLoop.instance().start()

class _UI(RequestHandler):
    def get(self):
        return self.render('meetling.html')

class Endpoint(RequestHandler):
    """JSON REST API endpoint.

    .. attribute:: server

       Context :class:`MeetlingServer`.

    .. attribute:: app

       :class:`Meetling` application.

    .. attribute:: args

       Dictionary of JSON arguments passed by the client.
    """

    def initialize(self):
        self.server = self.application.settings['server']
        self.app = self.server.app
        self.args = {}

    def prepare(self):
        self.app.user = None
        auth_secret = self.get_cookie('auth_secret')
        if auth_secret:
            self.app.authenticate(auth_secret)

        if self.request.body:
            try:
                self.args = json.loads(self.request.body.decode())
            except ValueError:
                raise HTTPError(http.client.BAD_REQUEST)
            if not isinstance(self.args, Mapping):
                raise HTTPError(http.client.BAD_REQUEST)

    def write_error(self, status_code, exc_info):
        if issubclass(exc_info[0], KeyError):
            self.set_status(http.client.NOT_FOUND)
            self.write({'__type__': 'NotFoundError'})
        elif issubclass(exc_info[0], meetling.AuthenticationError):
            self.set_status(http.client.BAD_REQUEST)
            self.write({'__type__': exc_info[0].__name__})
        elif issubclass(exc_info[0], meetling.PermissionError):
            self.set_status(http.client.FORBIDDEN)
            self.write({'__type__': exc_info[0].__name__})
        elif issubclass(exc_info[0], meetling.InputError):
            self.set_status(http.client.BAD_REQUEST)
            self.write({
                '__type__': exc_info[0].__name__,
                'code': exc_info[1].code,
                'errors': exc_info[1].errors
            })
        elif issubclass(exc_info[0], meetling.ValueError):
            self.set_status(http.client.BAD_REQUEST)
            self.write({'__type__': exc_info[0].__name__, 'code': exc_info[1].code})
        else:
            super().write_error(status_code, exc_info=exc_info)

    def log_exception(self, typ, value, tb):
        # These errors are handled specially and there is no need to log them as exceptions
        if issubclass(typ, (KeyError, meetling.AuthenticationError, meetling.PermissionError,
                            meetling.ValueError)):
            return
        super().log_exception(typ, value, tb)

    def check_args(self, type_info):
        """Check *args* for their expected type.

        *type_info* maps argument names to :class:`type` s. If multiple types are valid for an
        argument, a tuple can be given. The special keyword ``'opt'`` marks an argument as optional.
        ``None`` is equvialent to ``type(None)``. An example *type_info* could look like::

            {'name': str, 'pattern': (str, 'opt')}

        If any argument has an unexpected type, an :exc:`InputError` with ``bad_type`` is raised. If
        an argument is missing but required, an :exc:`InputError` with ``missing`` is raised.

        A filtered subset of *args* is returned, matching those present in *type_info*. Thus any
        excess argument passed by the client can safely be ignored.
        """
        args = {k: v for k, v in self.args.items() if k in type_info.keys()}

        e = meetling.InputError()
        for arg, types in type_info.items():
            # Normalize
            if not isinstance(types, tuple):
                types = (types, )
            types = tuple(type(None) if t is None else t for t in types)

            # Check
            if arg not in args:
                if 'opt' not in types:
                    e.errors[arg] = 'missing'
            else:
                types = tuple(t for t in types if isinstance(t, type))
                # TODO: Raise error if types is empty (e.g. if it contained only keywords)
                if not isinstance(args.get(arg), types):
                    e.errors[arg] = 'bad_type'
        e.trigger()

        return args

class _LogClientErrorEndpoint(Endpoint):
    def post(self):
        if not self.app.user:
            raise meetling.PermissionError()

        args = self.check_args({
            'type': str,
            'stack': str,
            'url': str,
            'message': (str, None, 'opt')
        })
        e = meetling.InputError()
        if str_or_none(args['type']) is None:
            e.errors['type'] = 'empty'
        if str_or_none(args['stack']) is None:
            e.errors['stack'] = 'empty'
        if str_or_none(args['url']) is None:
            e.errors['url'] = 'empty'
        e.trigger()

        message = str_or_none(args.get('message'))
        message_part = ': ' + message if message else ''
        _LOGGER.error(
            _CLIENT_ERROR_LOG_TEMPLATE, args['type'], message_part, args['stack'].strip(),
            args['url'], self.app.user.name, self.app.user.id,
            self.request.headers.get('user-agent', '-'))

class _ReplaceAuthEndpoint(RequestHandler):
    # Compatibility for server side authentication (obsolete since 0.10.0)

    def post(self):
        app = self.application.settings['server'].app
        app.user = None
        auth_secret = self.get_cookie('auth_secret')
        if auth_secret:
            try:
                app.authenticate(auth_secret)
            except meetling.AuthenticationError:
                pass
            self.clear_cookie('auth_secret')
        self.write(app.user.json(restricted=True) if app.user else 'null')

class _LoginEndpoint(Endpoint):
    def post(self):
        args = self.check_args({'code': (str, 'opt')})
        user = self.app.login(**args)
        self.write(user.json(restricted=True))

class _MeetingsEndpoint(Endpoint):
    def post(self):
        args = self.check_args({
            'title': str,
            'time': (str, None, 'opt'),
            'location': (str, None, 'opt'),
            'description': (str, None, 'opt')
        })
        if 'time' in args and args['time']:
            try:
                args['time'] = parse_isotime(args['time'])
            except ValueError:
                raise meetling.InputError({'time': 'bad_type'})

        meeting = self.app.create_meeting(**args)
        self.write(meeting.json(restricted=True, include_users=True))

class _CreateExampleMeetingEndpoint(Endpoint):
    def post(self):
        meeting = self.app.create_example_meeting()
        self.write(meeting.json(restricted=True, include_users=True))

class _UserEndpoint(Endpoint):
    def get(self, id):
        self.write(self.app.users[id].json(restricted=True))

    def post(self, id):
        args = self.check_args({'name': (str, 'opt')})
        user = self.app.users[id]
        user.edit(**args)
        self.write(user.json(restricted=True))

class _SettingsEndpoint(Endpoint):
    def get(self):
        self.write(self.app.settings.json(restricted=True, include_users=True))

    def post(self):
        args = self.check_args({
            'title': (str, 'opt'),
            'icon': (str, None, 'opt'),
            'favicon': (str, None, 'opt')
        })
        settings = self.app.settings
        settings.edit(**args)
        self.write(settings.json(restricted=True, include_users=True))

class _MeetingEndpoint(Endpoint):
    def get(self, id):
        meeting = self.app.meetings[id]
        self.write(meeting.json(restricted=True, include_users=True))

    def post(self, id):
        args = self.check_args({
            'title': (str, 'opt'),
            'time': (str, None, 'opt'),
            'location': (str, None, 'opt'),
            'description': (str, None, 'opt')
        })
        if 'time' in args and args['time']:
            try:
                args['time'] = parse_isotime(args['time'])
            except ValueError:
                raise meetling.InputError({'time': 'bad_type'})

        meeting = self.app.meetings[id]
        meeting.edit(**args)
        self.write(meeting.json(restricted=True, include_users=True))

class _MeetingItemsEndpoint(Endpoint):
    def get(self, id, set):
        meeting = self.app.meetings[id]
        items = meeting.trashed_items.values() if set else meeting.items.values()
        self.write(json.dumps([i.json(restricted=True, include_users=True) for i in items]))

    def post(self, id, set):
        if set:
            raise HTTPError(http.client.METHOD_NOT_ALLOWED)
        args = self.check_args({
            'title': str,
            'duration': (int, None, 'opt'),
            'description': (str, None, 'opt')
        })
        meeting = self.app.meetings[id]
        item = meeting.create_agenda_item(**args)
        self.write(item.json(restricted=True, include_users=True))

class _MeetingTrashAgendaItemEndpoint(Endpoint):
    def post(self, id):
        args = self.check_args({'item_id': str})
        meeting = self.app.meetings[id]
        try:
            args['item'] = meeting.items[args.pop('item_id')]
        except KeyError:
            raise meetling.ValueError('item_not_found')

        meeting.trash_agenda_item(**args)
        self.write(json.dumps(None))

class _MeetingRestoreAgendaItemEndpoint(Endpoint):
    def post(self, id):
        args = self.check_args({'item_id': str})
        meeting = self.app.meetings[id]
        try:
            args['item'] = meeting.trashed_items[args.pop('item_id')]
        except KeyError:
            raise meetling.ValueError('item_not_found')

        meeting.restore_agenda_item(**args)
        self.write(json.dumps(None))

class _MeetingMoveAgendaItemEndpoint(Endpoint):
    def post(self, id):
        args = self.check_args({'item_id': str, 'to_id': (str, None)})
        meeting = self.app.meetings[id]
        try:
            args['item'] = meeting.items[args.pop('item_id')]
        except KeyError:
            raise meetling.ValueError('item_not_found')
        args['to'] = args.pop('to_id')
        if args['to'] is not None:
            try:
                args['to'] = meeting.items[args['to']]
            except KeyError:
                raise meetling.ValueError('to_not_found')

        meeting.move_agenda_item(**args)
        self.write(json.dumps(None))

class _AgendaItemEndpoint(Endpoint):
    def get(self, meeting_id, item_id):
        meeting = self.app.meetings[meeting_id]
        item = meeting.items[item_id]
        self.write(item.json(restricted=True, include_users=True))

    def post(self, meeting_id, item_id):
        args = self.check_args({
            'title': (str, 'opt'),
            'duration': (int, None, 'opt'),
            'description': (str, None, 'opt')
        })
        meeting = self.app.meetings[meeting_id]
        item = meeting.items[item_id]
        item.edit(**args)
        self.write(item.json(restricted=True, include_users=True))
