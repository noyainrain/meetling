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
from meetling import Meetling, InputError

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
            (r'/$', StartPage),
            (r'/create-meeting$', EditMeetingPage),
            (r'/meetings/([^/]+)$', MeetingPage),
            (r'/meetings/([^/]+)/edit$', EditMeetingPage),
            (r'/api/meetings$', MeetingsEndpoint),
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
        self.listen(self.port)
        IOLoop.instance().start()

class Page(RequestHandler):
    def initialize(self):
        self.server = self.application.settings['server']
        self.app = self.server.app

class StartPage(Page):
    def get(self):
        self.render('start.html')

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

class Endpoint(RequestHandler):
    def initialize(self):
        self.server = self.application.settings['server']
        self.app = self.server.app
        self.args = {}

    def prepare(self):
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
        else:
            status_code = {KeyError: http.client.NOT_FOUND}.get(exc_info[0], status_code)
            self.set_status(status_code)
            super().write_error(status_code, exc_info=exc_info)

    def log_exception(self, typ, value, tb):
        # These errors are handled specially and there is no need to log them as exceptions
        if issubclass(typ, (InputError, KeyError)):
            return
        super().log_exception(typ, value, tb)

class MeetingsEndpoint(Endpoint):
    def post(self):
        args = {k: v for k, v in self.args.items() if k in ('title', 'description')}
        e = InputError()
        if not isinstance(args.get('title'), str):
            e.errors['title'] = 'bad_type'
        if not isinstance(args.get('description'), (str, type(None))):
            e.errors['description'] = 'bad_type'
        e.trigger()

        meeting = self.app.create_meeting(**args)
        self.write(meeting.json())

class MeetingEndpoint(Endpoint):
    def get(self, id):
        meeting = self.app.meetings[id]
        self.write(meeting.json())

    def post(self, id):
        args = {k: v for k, v in self.args.items() if k in ('title', 'description')}
        e = InputError()
        if not isinstance(args.get('title', ''), str):
            e.errors['title'] = 'bad_type'
        if not isinstance(args.get('description'), (str, type(None))):
            e.errors['description'] = 'bad_type'
        e.trigger()

        meeting = self.app.meetings[id]
        meeting.edit(**args)
        self.write(meeting.json())

class MeetingItemsEndpoint(Endpoint):
    def get(self, id):
        meeting = self.app.meetings[id]
        self.write(json.dumps([i.json() for i in meeting.items.values()]))

    def post(self, id):
        args = {k: v for k, v in self.args.items() if k in ('title', 'description')}
        e = InputError()
        if not isinstance(args.get('title'), str):
            e.errors['title'] = 'bad_type'
        if not isinstance(args.get('description'), (str, type(None))):
            e.errors['description'] = 'bad_type'
        e.trigger()

        meeting = self.app.meetings[id]
        item = meeting.create_agenda_item(**args)
        self.write(item.json())

class AgendaItemEndpoint(Endpoint):
    def get(self, meeting_id, item_id):
        meeting = self.app.meetings[meeting_id]
        item = meeting.items[item_id]
        self.write(item.json())

    def post(self, meeting_id, item_id):
        args = {k: v for k, v in self.args.items() if k in ('title', 'description')}
        e = InputError()
        if not isinstance(args.get('title', ''), str):
            e.errors['title'] = 'bad_type'
        if not isinstance(args.get('description'), (str, type(None))):
            e.errors['description'] = 'bad_type'
        e.trigger()

        meeting = self.app.meetings[meeting_id]
        item = meeting.items[item_id]
        item.edit(**args)
        self.write(item.json())
