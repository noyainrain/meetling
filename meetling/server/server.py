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

from collections import Mapping
import http.client
import json
import logging
import os
import re
from urllib.parse import urlparse

import micro
from micro import AuthRequest
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
            (r'/api/meetings/([^/]+)/subscribe$', _MeetingSubscribeEndpoint),
            (r'/api/meetings/([^/]+)/unsubscribe$', _MeetingUnsubscribeEndpoint),
            (r'/api/meetings/([^/]+)/items(/trashed)?$', _MeetingItemsEndpoint),
            (r'/api/meetings/([^/]+)/trash-agenda-item$', _MeetingTrashAgendaItemEndpoint),
            (r'/api/meetings/([^/]+)/restore-agenda-item$', _MeetingRestoreAgendaItemEndpoint),
            (r'/api/meetings/([^/]+)/move-agenda-item$', _MeetingMoveAgendaItemEndpoint),
            (r'/api/meetings/([^/]+)/items/([^/]+)$', _AgendaItemEndpoint)
        ]
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

        # TODO
        self.app.handle_notification = self._notify

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

    # TODO: refactor to render_notification_message
    def _notify(self, event, user, feed):
        #print('NOTIFY', event, user, feed)
        from tornado.template import filter_whitespace
        from textwrap import TextWrapper, wrap, fill, dedent
        import re

        template = self._message_templates.load(event.type)
        msg = template.generate(event=event, user=user, feed=feed, app=self.app,
                                server=self).decode()

        # 78 as suggested by mime spec
        wrapper = TextWrapper(width=78, replace_whitespace=False, break_long_words=False,
                              break_on_hyphens=False)
        ps = [filter_whitespace('oneline', p.strip()) for p in re.split(r'\n{2,}', msg)]
        subject = ps.pop(0)[9:]
        body = '\n\n'.join([wrapper.fill(p) for p in ps])

        self.send_mail('todo@example.org', user.email, subject, body)

    # TODO: see above
    def send_mail(self, frm, to, subject, content):
        """TODO."""
        from email.message import EmailMessage

        # TODO: set policy?
        msg = EmailMessage()
        msg['To'] = to
        msg['From'] = frm
        msg['Subject'] = subject
        msg.set_content(content)

        from smtplib import SMTP
        with SMTP(host='localhost', port='2525') as smtp:
            smtp.send_message(msg)
        #import email.charset
        #from email.charset import Charset
        #from email.message import Message
        #from email.mime.text import MIMEText

        #txt = 'foobar\u00dc'

        #charset = Charset('utf-8')
        #charset.header_encoding = email.charset.QP
        #charset.body_encoding = email.charset.QP

        #msg = Message()
        #msg['Subject'] = txt
        #msg['From'] = 'ui'
        #msg['To'] = 'aiaiai'
        #msg.set_payload(txt, charset)
        ## TODO: send here, for now log
        #xx
        #print(msg)


    # ALTERNATIVE, but only if complex view logic is needed
    #def _editable_edit_notification(self, event, subscriber, feed):
    #   if isinstance(event.object, Meeting):
    #       # ...
    #   else:
    #       # ...
    #def _meeting_edit_notification(self, event, subscriber, feed):
    #    self.render_notification('meeting-edit', subscriber=subscriber, feed=feed,
    #                             meeting=event.object)

class _UI(RequestHandler):
    def get(self):
        self.set_header('Cache-Control', 'no-cache')
        self.render('meetling.html')

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
                raise HTTPError(int(http.client.BAD_REQUEST))
            if not isinstance(self.args, Mapping):
                raise HTTPError(int(http.client.BAD_REQUEST))

        if self.request.method in {'GET', 'HEAD'}:
            self.set_header('Cache-Control', 'no-cache')

    def write_error(self, status_code, exc_info):
        if issubclass(exc_info[0], KeyError):
            self.set_status(int(http.client.NOT_FOUND))
            self.write({'__type__': 'NotFoundError'})
        elif issubclass(exc_info[0], micro.AuthenticationError):
            self.set_status(int(http.client.BAD_REQUEST))
            self.write({'__type__': exc_info[0].__name__})
        elif issubclass(exc_info[0], micro.PermissionError):
            self.set_status(int(http.client.FORBIDDEN))
            self.write({'__type__': exc_info[0].__name__})
        elif issubclass(exc_info[0], micro.InputError):
            self.set_status(int(http.client.BAD_REQUEST))
            self.write({
                '__type__': exc_info[0].__name__,
                'code': exc_info[1].code,
                'errors': exc_info[1].errors
            })
        elif issubclass(exc_info[0], micro.ValueError):
            self.set_status(int(http.client.BAD_REQUEST))
            self.write({'__type__': exc_info[0].__name__, 'code': exc_info[1].code})
        else:
            super().write_error(status_code, exc_info=exc_info)

    def log_exception(self, typ, value, tb):
        # These errors are handled specially and there is no need to log them as exceptions
        if issubclass(typ, (KeyError, micro.AuthenticationError, micro.PermissionError,
                            micro.ValueError)):
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

        e = micro.InputError()
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
                raise micro.InputError({'time': 'bad_type'})

        meeting = self.app.meetings[id]
        meeting.edit(**args)
        self.write(meeting.json(restricted=True, include_users=True))

class _MeetingSubscribeEndpoint(Endpoint):
    def post(self, id):
        meeting = self.app.meetings[id]
        meeting.subscribe()

class _MeetingUnsubscribeEndpoint(Endpoint):
    def post(self, id):
        meeting = self.app.meetings[id]
        meeting.unsubscribe()

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
