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

"""Test utilites."""

from urllib.parse import urljoin

from tornado.httpclient import AsyncHTTPClient
from tornado.testing import AsyncTestCase

from .micro import Application, Editable, Object, Settings

class ServerTestCase(AsyncTestCase):
    """Subclass API: Server test case.

    .. attribute:: server

       :class:`server.Server` under test. Must be set by subclass.

    .. attribute:: client_user

       :class:`User` interacting with the server. May be set by subclass.
    """

    def setUp(self):
        super().setUp()
        self.server = None
        self.client_user = None

    def request(self, url, **args):
        """Run a request against the given *url* path.

        The request is issued by :attr:`client_user`, if set. This is a convenient wrapper around
        :meth:`tornado.httpclient.AsyncHTTPClient.fetch` and *args* are passed through.
        """
        headers = args.pop('headers', {})
        if self.client_user:
            headers.update({'Cookie': 'auth_secret=' + self.client_user.auth_secret})
        return AsyncHTTPClient().fetch(urljoin(self.server.url, url), headers=headers, **args)

class CatApp(Application):
    """Simple application for testing purposes."""

    def __init__(self, redis_url=''):
        super().__init__(redis_url=redis_url)
        self.types.update({'Cat': Cat})

    def create_settings(self):
        return Settings(
            id='Settings', trashed=False, app=self, authors=[], title='CatApp', icon=None,
            favicon=None, provider_name=None, provider_url=None, provider_description={},
            feedback_url=None, staff=[])

    def sample(self):
        """Set up some sample data."""
        user = self.login()
        auth_request = user.set_email('happy@example.org')
        self.r.set('auth_request', auth_request.id)

class Cat(Object, Editable):
    """Cute cat."""

    def __init__(self, id, trashed, app, authors, name):
        super().__init__(id, trashed, app)
        Editable.__init__(self, authors)
        self.name = name

    def do_edit(self, **attrs):
        if 'name' in attrs:
            self.name = attrs['name']

    def json(self, restricted=False, include=False):
        json = super().json(restricted=restricted, include=include)
        json.update(Editable.json(self, restricted=restricted, include=include))
        json.update({'name': self.name})
        return json
