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

"""micro application example."""

import json
import sys

import micro
from micro import Application, Editable, Object, Settings
from micro.jsonredis import JSONRedisMapping
from micro.server import Server, Endpoint
from micro.util import make_command_line_parser, randstr, setup_logging, str_or_none

class Hello(Application):
    """Hello application.

    .. attribute:: greetings

       Map of all :class:`Greeting` s.
    """

    def __init__(self, redis_url='', email='bot@localhost', smtp_url='',
                 render_email_auth_message=None):
        super().__init__(redis_url, email, smtp_url, render_email_auth_message)
        self.types.update({'Greeting': Greeting})
        self.greetings = JSONRedisMapping(self.r, 'greetings')

    def create_settings(self):
        return Settings(
            id='Settings', trashed=False, app=self, authors=[], title='Hello', icon=None,
            favicon=None, provider_name=None, provider_url=None, provider_description={},
            feedback_url=None, staff=[])

    def create_greeting(self, text):
        """Create a :class:`Greeting` and return it."""
        if str_or_none(text) is None:
            raise micro.ValueError('text_empty')
        greeting = Greeting(id=randstr(), trashed=False, app=self, authors=[self.user.id],
                            text=text)
        self.r.oset(greeting.id, greeting)
        self.r.rpush('greetings', greeting.id)
        return greeting

class Greeting(Object, Editable):
    """Public greeting.

    .. attribute:: text

       Text content.
    """

    def __init__(self, id, trashed, app, authors, text):
        super().__init__(id, trashed, app)
        Editable.__init__(self, authors)
        self.text = text

    def do_edit(self, **attrs):
        if 'text' in attrs:
            if str_or_none(attrs['text']) is None:
                raise micro.ValueError('text_empty')
            self.text = attrs['text']

    def json(self, restricted=False, include=False):
        # pylint: disable=redefined-outer-name; fine name
        json = super().json(restricted, include)
        json.update(Editable.json(self, restricted, include))
        json.update({'text': self.text})
        return json

def make_server(port=8080, url=None, client_path='.', debug=False, redis_url='', smtp_url=''):
    """Create a Hello server."""
    app = Hello(redis_url, smtp_url=smtp_url)
    handlers = [(r'/api/greetings$', _GreetingsEndpoint)]
    return Server(app, handlers, port, url, client_path, 'node_modules', debug)

class _GreetingsEndpoint(Endpoint):
    # pylint: disable=abstract-method; Tornado handlers define a semi-abstract data_received()
    # pylint: disable=arguments-differ; Tornado handler arguments are defined by URLs

    def get(self):
        greetings = self.app.greetings.values()
        self.write(json.dumps([g.json(restricted=True, include=True) for g in greetings]))

    def post(self):
        args = self.check_args({'text': str})
        greeting = self.app.create_greeting(**args)
        self.write(greeting.json(restricted=True, include=True))

def main(args):
    """Run Hello.

    *args* is the list of command line arguments.
    """
    args = make_command_line_parser().parse_args(args[1:])
    setup_logging(args.debug if 'debug' in args else False)
    make_server(**vars(args)).run()
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
