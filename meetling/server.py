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

"""Meetling server."""

import os
import json
import http.client
import meetling
from collections import Mapping
from tornado.httpserver import HTTPServer
from tornado.web import Application, RequestHandler, HTTPError
from tornado.ioloop import IOLoop
from meetling import Meetling, InputError, PermissionError

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
            (r'/$', StartPage),
            (r'/about$', AboutPage),
            (r'/create-meeting$', EditMeetingPage),
            (r'/settings/edit$', EditSettingsPage),
            (r'/meetings/([^/]+)$', MeetingPage),
            (r'/meetings/([^/]+)/edit$', EditMeetingPage),
            # API
            (r'/api/login$', LoginEndpoint),
            (r'/api/meetings$', MeetingsEndpoint),
            (r'/api/create-example-meeting$', CreateExampleMeetingEndpoint),
            (r'/api/users/([^/]+)$', UserEndpoint),
            (r'/api/settings$', SettingsEndpoint),
            (r'/api/meetings/([^/]+)$', MeetingEndpoint),
            (r'/api/meetings/([^/]+)/items$', MeetingItemsEndpoint),
            (r'/api/meetings/([^/]+)/items/([^/]+)$', AgendaItemEndpoint)
        ]
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

class Resource(RequestHandler):
    """Web resource.

    .. attribute:: server

       Context :class:`MeetlingServer`.

    .. attribute:: app

       :class:`Meetling` application.
    """

    def initialize(self):
        self.server = self.application.settings['server']
        self.app = self.server.app

    def prepare(self):
        self.app.user = None
        auth_secret = self.get_cookie('auth_secret')
        if auth_secret:
            try:
                self.app.authenticate(auth_secret)
            except ValueError:
                # Ignore invalid authentication secrets
                pass

class Page(Resource):
    def prepare(self):
        super().prepare()

        # If requested, log in with code
        login_code = self.get_query_argument('login', None)
        if login_code:
            try:
                user = self.app.authenticate(login_code)
            except ValueError:
                # Ignore invalid login codes
                pass
            else:
                self.set_cookie('auth_secret', user.auth_secret, expires_days=360, httponly=True)

        # If not authenticated yet, log in a new user
        if not self.app.user:
            user = self.app.login()
            self.set_cookie('auth_secret', user.auth_secret, expires_days=360, httponly=True)

    def get_template_namespace(self):
        return {'user': self.app.user, 'settings': self.app.settings}

class StartPage(Page):
    def get(self):
        self.render('start.html')

class AboutPage(Page):
    def get(self):
        self.render('about.html')

class EditSettingsPage(Page):
    def get(self):
        self.render('edit-settings.html')

class MeetingPage(Page):
    def get(self, id):
        try:
            meeting = self.app.meetings[id]
        except KeyError:
            raise HTTPError(http.client.NOT_FOUND)
        self.render('meeting.html', meeting=meeting)

class EditMeetingPage(Page):
    def get(self, id=None):
        try:
            meeting = self.app.meetings[id] if id else None
        except KeyError:
            raise HTTPError(http.client.NOT_FOUND)
        self.render('edit-meeting.html', meeting=meeting)

class Endpoint(Resource):
    """JSON REST API endpoint.

    .. attribute:: args

       Dictionary of JSON arguments passed by the client.
    """

    def initialize(self):
        super().initialize()
        self.args = {}

    def prepare(self):
        super().prepare()
        if self.request.body:
            try:
                self.args = json.loads(self.request.body.decode())
            except ValueError:
                raise HTTPError(http.client.BAD_REQUEST)
            if not isinstance(self.args, Mapping):
                raise HTTPError(http.client.BAD_REQUEST)

    def write_error(self, status_code, exc_info):
        if issubclass(exc_info[0], InputError):
            self.set_status(http.client.BAD_REQUEST)
            self.write({'__type__': exc_info[0].__name__, 'errors': exc_info[1].errors})
        elif issubclass(exc_info[0], PermissionError):
            self.set_status(http.client.FORBIDDEN)
            self.write({'__type__': exc_info[0].__name__})
        else:
            status_code = {KeyError: http.client.NOT_FOUND}.get(exc_info[0], status_code)
            self.set_status(status_code)
            super().write_error(status_code, exc_info=exc_info)

    def log_exception(self, typ, value, tb):
        # These errors are handled specially and there is no need to log them as exceptions
        if issubclass(typ, (InputError, PermissionError, KeyError)):
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

        e = InputError()
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

class LoginEndpoint(Endpoint):
    def post(self):
        user = self.app.login()
        self.write(user.json())

class MeetingsEndpoint(Endpoint):
    def post(self):
        args = self.check_args({'title': str, 'description': (str, None, 'opt')})
        meeting = self.app.create_meeting(**args)
        self.write(meeting.json())

class CreateExampleMeetingEndpoint(Endpoint):
    def post(self):
        meeting = self.app.create_example_meeting()
        self.write(meeting.json())

class UserEndpoint(Endpoint):
    def get(self, id):
        self.write(self.app.users[id].json(exclude_private=True))

class SettingsEndpoint(Endpoint):
    def get(self):
        self.write(self.app.settings.json(include_users=True))

    def post(self):
        args = self.check_args({
            'title': (str, 'opt'),
            'icon': (str, None, 'opt'),
            'favicon': (str, None, 'opt')
        })
        settings = self.app.settings
        settings.edit(**args)
        self.write(settings.json(include_users=True))

class MeetingEndpoint(Endpoint):
    def get(self, id):
        meeting = self.app.meetings[id]
        self.write(meeting.json())

    def post(self, id):
        args = self.check_args({'title': (str, 'opt'), 'description': (str, None, 'opt')})
        meeting = self.app.meetings[id]
        meeting.edit(**args)
        self.write(meeting.json())

class MeetingItemsEndpoint(Endpoint):
    def get(self, id):
        meeting = self.app.meetings[id]
        self.write(json.dumps([i.json() for i in meeting.items.values()]))

    def post(self, id):
        args = self.check_args({'title': str, 'description': (str, None, 'opt')})
        meeting = self.app.meetings[id]
        item = meeting.create_agenda_item(**args)
        self.write(item.json())

class AgendaItemEndpoint(Endpoint):
    def get(self, meeting_id, item_id):
        meeting = self.app.meetings[meeting_id]
        item = meeting.items[item_id]
        self.write(item.json())

    def post(self, meeting_id, item_id):
        args = self.check_args({'title': (str, 'opt'), 'description': (str, None, 'opt')})
        meeting = self.app.meetings[meeting_id]
        item = meeting.items[item_id]
        item.edit(**args)
        self.write(item.json())
