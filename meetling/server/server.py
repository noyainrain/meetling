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

# pylint: disable=abstract-method; Tornado handlers define a semi-abstract data_received()
# pylint: disable=arguments-differ; Tornado handler arguments are defined by URLs

"""Meetling server core."""

import http.client
import json
import logging
import os
import re
from urllib.parse import urlparse

import micro
from micro import AuthRequest
from micro.server import Endpoint, make_list_endpoints
from micro.util import str_or_none, parse_isotime
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.template import DictLoader, filter_whitespace
from tornado.web import Application, RequestHandler, HTTPError

import meetling
from meetling import Meetling
import meetling.server.templates

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

    .. attribute:: url

       See ``--url`` command line option.

    .. attribute:: debug

       See ``--debug`` command line option.

    Additional *args* are passed to the :class:`meetling.Meetling` constructor and any errors raised
    by it are passed through.
    """

    def __init__(self, port=8080, url=None, debug=False, **args):
        # pylint: disable=super-init-not-called; Configurable classes use initialize() instead of
        #                                        __init__()
        url = url or 'http://localhost:{}'.format(port)
        try:
            urlparts = urlparse(url)
        except ValueError:
            raise ValueError('url_invalid')
        not_allowed = {'username', 'password', 'path', 'params', 'query', 'fragment'}
        if not (urlparts.scheme in {'http', 'https'} and urlparts.hostname and
                not any(getattr(urlparts, k) for k in not_allowed)):
            raise ValueError('url_invalid')

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
            (r'/api/users/([^/]+)/set-email$', _UserSetEmailEndpoint),
            (r'/api/users/([^/]+)/finish-set-email$', _UserFinishSetEmailEndpoint),
            (r'/api/users/([^/]+)/remove-email$', _UserRemoveEmailEndpoint),
            (r'/api/settings$', _SettingsEndpoint),
            (r'/api/meetings/([^/]+)$', _MeetingEndpoint),
            (r'/api/meetings/([^/]+)/items(/trashed)?$', _MeetingItemsEndpoint),
            (r'/api/meetings/([^/]+)/trash-agenda-item$', _MeetingTrashAgendaItemEndpoint),
            (r'/api/meetings/([^/]+)/restore-agenda-item$', _MeetingRestoreAgendaItemEndpoint),
            (r'/api/meetings/([^/]+)/move-agenda-item$', _MeetingMoveAgendaItemEndpoint),
            (r'/api/meetings/([^/]+)/items/([^/]+)$', _AgendaItemEndpoint)
        ]
        handlers += make_list_endpoints(r'/api/activity', lambda *a: self.app.activity)
        # pylint: disable=protected-access; meetling is a friend
        application = Application(
            handlers, compress_response=True,
            template_path=os.path.join(meetling._RES_PATH, 'templates'),
            static_path=os.path.join(meetling._RES_PATH, 'static'), debug=debug, server=self)
        super().initialize(application)

        self.port = port
        self.url = url
        self.debug = debug
        self.app = Meetling(email='bot@' + urlparts.hostname,
                            render_email_auth_message=self._render_email_auth_message, **args)

        self._message_templates = DictLoader(meetling.server.templates.MESSAGE_TEMPLATES,
                                             autoescape=None)

    def initialize(self, *args, **kwargs):
        # Configurable classes call initialize() instead of __init__()
        self.__init__(*args, **kwargs)

    def run(self):
        """Run the server."""
        self.app.update()
        self.listen(self.port)
        IOLoop.instance().start()

    def _render_email_auth_message(self, email, auth_request, auth):
        template = self._message_templates.load('email_auth')
        msg = template.generate(email=email, auth_request=auth_request, auth=auth, app=self.app,
                                server=self).decode()
        return '\n\n'.join([filter_whitespace('oneline', p.strip()) for p in
                            re.split(r'\n{2,}', msg)])

class _UI(RequestHandler):
    def get(self):
        self.set_header('Cache-Control', 'no-cache')
        self.render('meetling.html')

class _LogClientErrorEndpoint(Endpoint):
    def post(self):
        if not self.app.user:
            raise micro.PermissionError()

        args = self.check_args({
            'type': str,
            'stack': str,
            'url': str,
            'message': (str, None, 'opt')
        })
        e = micro.InputError()
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
            except micro.AuthenticationError:
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
                raise micro.InputError({'time': 'bad_type'})

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
        user = self.app.users[id]
        args = self.check_args({'name': (str, 'opt')})
        user.edit(**args)
        self.write(user.json(restricted=True))

class _UserSetEmailEndpoint(Endpoint):
    def post(self, id):
        user = self.app.users[id]
        args = self.check_args({'email': str})
        auth_request = user.set_email(**args)
        self.write(auth_request.json(restricted=True))

class _UserFinishSetEmailEndpoint(Endpoint):
    def post(self, id):
        user = self.app.users[id]
        args = self.check_args({'auth_request_id': str, 'auth': str})
        args['auth_request'] = self.app.get_object(args.pop('auth_request_id'), None)
        if not isinstance(args['auth_request'], AuthRequest):
            raise micro.ValueError('auth_request_not_found')
        user.finish_set_email(**args)
        self.write(user.json(restricted=True))

class _UserRemoveEmailEndpoint(Endpoint):
    def post(self, id):
        user = self.app.users[id]
        user.remove_email()
        self.write(user.json(restricted=True))

class _SettingsEndpoint(Endpoint):
    def get(self):
        self.write(self.app.settings.json(restricted=True, include_users=True))

    def post(self):
        args = self.check_args({
            'title': (str, 'opt'),
            'icon': (str, None, 'opt'),
            'favicon': (str, None, 'opt'),
            'feedback_url': (str, None, 'opt')
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
                raise micro.InputError({'time': 'bad_type'})

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
            raise HTTPError(int(http.client.METHOD_NOT_ALLOWED))
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
            raise micro.ValueError('item_not_found')

        meeting.trash_agenda_item(**args)
        self.write(json.dumps(None))

class _MeetingRestoreAgendaItemEndpoint(Endpoint):
    def post(self, id):
        args = self.check_args({'item_id': str})
        meeting = self.app.meetings[id]
        try:
            args['item'] = meeting.trashed_items[args.pop('item_id')]
        except KeyError:
            raise micro.ValueError('item_not_found')

        meeting.restore_agenda_item(**args)
        self.write(json.dumps(None))

class _MeetingMoveAgendaItemEndpoint(Endpoint):
    def post(self, id):
        args = self.check_args({'item_id': str, 'to_id': (str, None)})
        meeting = self.app.meetings[id]
        try:
            args['item'] = meeting.items[args.pop('item_id')]
        except KeyError:
            raise micro.ValueError('item_not_found')
        args['to'] = args.pop('to_id')
        if args['to'] is not None:
            try:
                args['to'] = meeting.items[args['to']]
            except KeyError:
                raise micro.ValueError('to_not_found')

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
