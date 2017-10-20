# micro
# Copyright (C) 2017 micro contributors
#
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU
# Lesser General Public License as published by the Free Software Foundation, either version 3 of
# the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without
# even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License along with this program.
# If not, see <http://www.gnu.org/licenses/>.

# pylint: disable=abstract-method; Tornado handlers define a semi-abstract data_received()
# pylint: disable=arguments-differ; Tornado handler arguments are defined by URLs

"""Server components."""

from collections import Mapping
import http.client
import json
from logging import getLogger
import os
import re
from urllib.parse import urlparse

from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.template import DictLoader, Loader, filter_whitespace
from tornado.web import Application, RequestHandler, HTTPError

from . import micro, templates
from .micro import AuthRequest, Object, InputError, AuthenticationError, PermissionError
from .util import str_or_none, parse_slice, check_polyglot

LIST_LIMIT = 100

_CLIENT_ERROR_LOG_TEMPLATE = """\
Client error occurred
%s%s
Stack:
%s
URL: %s
User: %s (%s)
Device info: %s"""

_LOGGER = getLogger(__name__)

class Server:
    """Server for micro apps.

    .. attribute:: app

       Underlying :class:`micro.Application`.

    .. attribute:: handlers

       Table of request handlers.

       It is a list of tuples, mapping a URL regular expression pattern to a
       :class:`tornado.web.RequestHandler` class.

    .. attribute:: port

       See ``--port`` command line option.

    .. attribute:: url

       See ``--url`` command line option.

    .. attributes:: client_path

       Client location from where static files and templates are delivered.

    .. attribute:: debug

       See ``--debug`` command line option.
    """
    def __init__(self, app, handlers, port=8080, url=None, client_path='client',
                 client_modules_path='.', debug=False):
        url = url or 'http://localhost:{}'.format(port)
        try:
            urlparts = urlparse(url)
        except ValueError:
            raise ValueError('url_invalid')
        not_allowed = {'username', 'password', 'path', 'params', 'query', 'fragment'}
        if not (urlparts.scheme in {'http', 'https'} and urlparts.hostname and
                not any(getattr(urlparts, k) for k in not_allowed)):
            raise ValueError('url_invalid')

        self.app = app
        self.port = port
        self.url = url
        self.client_path = client_path
        self.client_modules_path = client_modules_path
        self.debug = debug

        self.app.email = 'bot@' + urlparts.hostname
        self.app.render_email_auth_message = self._render_email_auth_message

        self.handlers = [
            # UI
            (r'/log-client-error$', _LogClientErrorEndpoint),
            (r'/(?!api/).*$', _UI),
            # API
            (r'/api/login$', _LoginEndpoint),
            (r'/api/users/([^/]+)$', _UserEndpoint),
            (r'/api/users/([^/]+)/set-email$', _UserSetEmailEndpoint),
            (r'/api/users/([^/]+)/finish-set-email$', _UserFinishSetEmailEndpoint),
            (r'/api/users/([^/]+)/remove-email$', _UserRemoveEmailEndpoint),
            (r'/api/settings$', _SettingsEndpoint),
        ]
        self.handlers += make_list_endpoints(r'/api/activity', lambda *a: self.app.activity)
        self.handlers += handlers

        self._server = HTTPServer(Application(
            self.handlers, compress_response=True, template_path=self.client_path,
            static_path=self.client_path, debug=self.debug, server=self))
        self._message_templates = DictLoader(templates.MESSAGE_TEMPLATES, autoescape=None)
        self._micro_templates = Loader(os.path.join(self.client_path, self.client_modules_path,
                                                    'micro'))

    def start(self):
        """Start the server."""
        self.app.update()
        self._server.listen(self.port)

    def run(self):
        """Start the server and run it continuously."""
        self.start()
        try:
            IOLoop.instance().start()
        except KeyboardInterrupt:
            pass

    def _render_email_auth_message(self, email, auth_request, auth):
        template = self._message_templates.load('email_auth')
        msg = template.generate(email=email, auth_request=auth_request, auth=auth, app=self.app,
                                server=self).decode()
        return '\n\n'.join([filter_whitespace('oneline', p.strip()) for p in
                            re.split(r'\n{2,}', msg)])

class Endpoint(RequestHandler):
    """JSON REST API endpoint.

    .. attribute:: server

       Context server.

    .. attribute:: app

       Context :class:`Application`.

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

        if self.request.method in {'GET', 'HEAD'}:
            self.set_header('Cache-Control', 'no-cache')

    def write_error(self, status_code, exc_info):
        if issubclass(exc_info[0], KeyError):
            self.set_status(http.client.NOT_FOUND)
            self.write({'__type__': 'NotFoundError'})
        elif issubclass(exc_info[0], AuthenticationError):
            self.set_status(http.client.BAD_REQUEST)
            self.write({'__type__': exc_info[0].__name__})
        elif issubclass(exc_info[0], PermissionError):
            self.set_status(http.client.FORBIDDEN)
            self.write({'__type__': exc_info[0].__name__})
        elif issubclass(exc_info[0], InputError):
            self.set_status(http.client.BAD_REQUEST)
            self.write({
                '__type__': exc_info[0].__name__,
                'code': exc_info[1].code,
                'errors': exc_info[1].errors
            })
        elif issubclass(exc_info[0], micro.ValueError):
            self.set_status(http.client.BAD_REQUEST)
            self.write({'__type__': exc_info[0].__name__, 'code': exc_info[1].code})
        else:
            super().write_error(status_code, exc_info=exc_info)

    def log_exception(self, typ, value, tb):
        # These errors are handled specially and there is no need to log them as exceptions
        if issubclass(typ, (KeyError, AuthenticationError, PermissionError, micro.ValueError)):
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
                # NOTE: We currently do not handle types being empty (e.g. it contained only
                # keywords)
                if not isinstance(args.get(arg), types):
                    e.errors[arg] = 'bad_type'
        e.trigger()

        return args

def make_list_endpoints(url, get_list):
    """Make the API endpoints for a list with support for slicing.

    *url* is the URL of the list.

    *get_list* is a hook of the form *get_list(*args)*, responsible for retrieving the underlying
    list. *args* are the URL arguments.
    """
    return [(url + r'(?:/(\d*:\d*))?$', _ListEndpoint, {'get_list': get_list})]

class _UI(RequestHandler):
    def initialize(self):
        self._server = self.application.settings['server']
        # pylint: disable=protected-access; Server is a friend
        self._templates = self._server._micro_templates
        if self._server.debug:
            self._templates.reset()

    def get(self):
        self.set_header('Cache-Control', 'no-cache')
        self.render(
            'index.html', micro_dependencies=self._render_micro_dependencies,
            micro_boot=self._render_micro_boot, micro_templates=self._render_micro_templates)

    def _render_micro_dependencies(self):
        return self._templates.load('dependencies.html').generate(
            static_url=self.static_url, modules_path=self._server.client_modules_path)

    def _render_micro_boot(self):
        return self._templates.load('boot.html').generate()

    def _render_micro_templates(self):
        return self._templates.load('templates.html').generate()

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

class _ListEndpoint(Endpoint):
    def initialize(self, get_list):
        super().initialize()
        self.get_list = get_list

    def get(self, *args):
        seq = self.get_list(*args)
        slice = parse_slice(args[-1] or ':', limit=LIST_LIMIT)
        self.write(json.dumps([i.json(restricted=True, include=True) if isinstance(i, Object) else i
                               for i in seq[slice]]))
class _LoginEndpoint(Endpoint):
    def post(self):
        args = self.check_args({'code': (str, 'opt')})
        user = self.app.login(**args)
        self.write(user.json(restricted=True))

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
        self.write(self.app.settings.json(restricted=True, include=True))

    def post(self):
        args = self.check_args({
            'title': (str, 'opt'),
            'icon': (str, None, 'opt'),
            'favicon': (str, None, 'opt'),
            'provider_name': (str, None, 'opt'),
            'provider_url': (str, None, 'opt'),
            'provider_description': (dict, 'opt'),
            'feedback_url': (str, None, 'opt')
        })
        if 'provider_description' in args:
            try:
                check_polyglot(args['provider_description'])
            except ValueError:
                raise micro.ValueError('provider_description_bad_type')

        settings = self.app.settings
        settings.edit(**args)
        self.write(settings.json(restricted=True, include=True))
