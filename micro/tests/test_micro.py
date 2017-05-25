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

# pylint: disable=missing-docstring; test module

from subprocess import check_call
from tempfile import mkdtemp

from redis import RedisError
from tornado.testing import AsyncTestCase

import micro
from micro import Application, Object, Editable, Settings, Activity, Event

SETUP_DB_SCRIPT = """\
from micro.tests.test_micro import CatApp
app = CatApp(redis_url='15')
app.r.flushdb()
app.update()
# Compatibility for CatApp without sample (obsolete since 0.13.0)
if hasattr(app, 'sample'):
    app.sample()
"""

class MicroTestCase(AsyncTestCase):
    def setUp(self):
        super().setUp()
        self.app = CatApp(redis_url='15')
        self.app.r.flushdb()
        self.app.update()
        self.staff_member = self.app.login()
        self.user = self.app.login()

class ApplicationTest(MicroTestCase):
    def test_init_redis_url_invalid(self):
        with self.assertRaisesRegex(micro.ValueError, 'redis_url_invalid'):
            CatApp(redis_url='//localhost:foo')

    def test_authenticate(self):
        user = self.app.authenticate(self.user.auth_secret)
        self.assertEqual(user, self.user)
        self.assertEqual(user, self.app.user)

    def test_authenticate_secret_invalid(self):
        with self.assertRaises(micro.AuthenticationError):
            self.app.authenticate('foo')

    def test_login(self):
        # login() is called by setUp()
        self.assertIn(self.user.id, self.app.users)
        self.assertEqual(self.user, self.app.user)
        self.assertIn(self.staff_member, self.app.settings.staff)

    def test_login_no_redis(self):
        app = CatApp(redis_url='//localhost:16160')
        with self.assertRaises(RedisError):
            app.login()

    def test_login_code(self):
        user = self.app.login(code=self.staff_member.auth_secret)
        self.assertEqual(user, self.staff_member)

    def test_login_code_invalid(self):
        with self.assertRaisesRegex(micro.ValueError, 'code_invalid'):
            self.app.login(code='foo')

class ApplicationUpdateTest(AsyncTestCase):
    @staticmethod
    def setup_db(tag):
        d = mkdtemp()
        check_call(['git', '-c', 'advice.detachedHead=false', 'clone', '-q', '--single-branch',
                    '--branch', tag, '.', d])
        check_call(['python3', '-c', SETUP_DB_SCRIPT], cwd=d)

    def test_update_db_fresh(self):
        app = CatApp(redis_url='15')
        app.r.flushdb()
        app.update()
        self.assertEqual(app.settings.title, 'CatApp')

    def test_update_db_version_previous(self):
        self.setup_db('0.14.0')
        app = CatApp(redis_url='15')
        app.update()

        self.assertFalse(app.settings.provider_description)

    def test_update_db_version_first(self):
        self.setup_db('0.12.3')
        app = CatApp(redis_url='15')
        app.update()

        # Update to version 2
        self.assertIsNone(app.settings.feedback_url)
        # Update to version 3
        self.assertFalse(app.settings.provider_description)

class EditableTest(MicroTestCase):
    def setUp(self):
        super().setUp()
        self.cat = Cat(id='Cat', trashed=False, app=self.app, authors=[], name=None)

    def test_edit(self):
        self.cat.edit(name='Happy')
        self.cat.edit(name='Grumpy')
        user2 = self.app.login()
        self.cat.edit(name='Hover')
        self.assertEqual(self.cat.authors, [self.user, user2])

    def test_edit_cat_trashed(self):
        self.cat.trashed = True
        with self.assertRaisesRegex(micro.ValueError, 'object_trashed'):
            self.cat.edit(name='Happy')

    def test_edit_user_anonymous(self):
        self.app.user = None
        with self.assertRaises(micro.PermissionError):
            self.cat.edit(name='Happy')

class UserTest(MicroTestCase):
    def test_edit(self):
        self.user.edit(name='Happy')
        self.assertEqual(self.user.name, 'Happy')

class ActivityTest(MicroTestCase):
    def test_publish(self):
        activity = Activity('more_activity', app=self.app)
        event = Event.create('meow', None, app=self.app)
        activity.publish(event)
        self.assertIn(event, activity)

class CatApp(Application):
    def __init__(self, redis_url=''):
        super().__init__(redis_url=redis_url)
        self.types.update({'Cat': Cat})

    def create_settings(self):
        return Settings(
            id='Settings', trashed=False, app=self, authors=[], title='CatApp', icon=None,
            favicon=None, provider_name=None, provider_url=None, provider_description={},
            feedback_url=None, staff=[])

    def sample(self):
        user = self.login()
        auth_request = user.set_email('happy@example.org')
        self.r.set('auth_request', auth_request.id)

class Cat(Object, Editable):
    def __init__(self, id, trashed, app, authors, name):
        super().__init__(id=id, trashed=trashed, app=app)
        Editable.__init__(self, authors=authors)
        self.name = name

    def do_edit(self, **attrs):
        if 'name' in attrs:
            self.name = attrs['name']

    def json(self, restricted=False, include=False):
        json = super().json(restricted=restricted, include=include)
        json.update(Editable.json(self, restricted=restricted, include=include))
        json.update({'name': self.name})
        return json
