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

"""Server components."""

import builtins
from collections import Mapping
import http.client
import json

from tornado.web import RequestHandler, HTTPError

from micro import ValueError, InputError, AuthenticationError, PermissionError

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
            except builtins.ValueError:
                raise HTTPError(int(http.client.BAD_REQUEST))
            if not isinstance(self.args, Mapping):
                raise HTTPError(int(http.client.BAD_REQUEST))

        if self.request.method in {'GET', 'HEAD'}:
            self.set_header('Cache-Control', 'no-cache')

    def write_error(self, status_code, exc_info):
        if issubclass(exc_info[0], KeyError):
            self.set_status(int(http.client.NOT_FOUND))
            self.write({'__type__': 'NotFoundError'})
        elif issubclass(exc_info[0], AuthenticationError):
            self.set_status(int(http.client.BAD_REQUEST))
            self.write({'__type__': exc_info[0].__name__})
        elif issubclass(exc_info[0], PermissionError):
            self.set_status(int(http.client.FORBIDDEN))
            self.write({'__type__': exc_info[0].__name__})
        elif issubclass(exc_info[0], InputError):
            self.set_status(int(http.client.BAD_REQUEST))
            self.write({
                '__type__': exc_info[0].__name__,
                'code': exc_info[1].code,
                'errors': exc_info[1].errors
            })
        elif issubclass(exc_info[0], ValueError):
            self.set_status(int(http.client.BAD_REQUEST))
            self.write({'__type__': exc_info[0].__name__, 'code': exc_info[1].code})
        else:
            super().write_error(status_code, exc_info=exc_info)

    def log_exception(self, typ, value, tb):
        # These errors are handled specially and there is no need to log them as exceptions
        if issubclass(typ, (KeyError, AuthenticationError, PermissionError, ValueError)):
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
