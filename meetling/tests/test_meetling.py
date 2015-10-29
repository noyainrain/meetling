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

# pylint: disable=missing-docstring

import subprocess
from subprocess import check_output
from tempfile import mkdtemp
from redis import RedisError
from tornado.testing import AsyncTestCase
from meetling import Meetling, Object, Editable, InputError, PermissionError

class MeetlingTestCase(AsyncTestCase):
    def setUp(self):
        super().setUp()
        self.app = Meetling(redis_url='15')
        self.app.r.flushdb()
        self.app.update()
        self.staff_member = self.app.login()
        self.user = self.app.login()

class MeetlingTest(MeetlingTestCase):
    def test_init_redis_url_invalid(self):
        with self.assertRaises(InputError):
            Meetling(redis_url='//localhost:foo')

    def test_authenticate(self):
        user = self.app.authenticate(self.user.auth_secret)
        self.assertEqual(user, self.user)
        self.assertEqual(user, self.app.user)

    def test_authenticate_secret_invalid(self):
        with self.assertRaisesRegex(ValueError, 'secret_invalid'):
            self.app.authenticate('foo')

    def test_login(self):
        # login() is called by setUp()
        self.assertIn(self.user.id, self.app.users)
        self.assertEqual(self.user, self.app.user)
        self.assertIn(self.staff_member, self.app.settings.staff)

    def test_create_meeting(self):
        meeting = self.app.create_meeting('Cat Hangout', '  ')
        self.assertIn(meeting.id, self.app.meetings)
        # Whitespace-only strings should be converted to None
        self.assertIsNone(meeting.description)

    def test_create_meeting_title_empty(self):
        with self.assertRaises(InputError):
            self.app.create_meeting('  ')

    def test_create_meeting_user_anonymous(self):
        self.app.user = None
        with self.assertRaises(PermissionError):
            self.app.create_meeting('Cat hangout')

    def test_create_meeting_no_redis(self):
        app = Meetling(redis_url='//localhoax')
        with self.assertRaises(RedisError):
            app.login()

    def test_create_example_meeting(self):
        meeting = self.app.create_example_meeting()
        self.assertTrue(len(meeting.items))

class MeetlingUpdateTest(AsyncTestCase):
    def test_update_db_fresh(self):
        app = Meetling(redis_url='15')
        app.r.flushdb()
        app.update()
        self.assertEqual(app.settings.title, 'My Meetling')

    def test_update_db_version_previous(self):
        self.setup_db('0.6.0')
        app = Meetling(redis_url='15')
        app.update()
        user = app.settings.staff[0]
        self.assertEqual(user.name, 'Guest')
        self.assertEqual(user.authors, [user])

    def test_update_db_version_first(self):
        self.setup_db('0.5.0')
        app = Meetling(redis_url='15')
        app.update()
        # update to version 2
        user = app.settings.staff[0]
        self.assertEqual(user.name, 'Guest')
        self.assertEqual(user.authors, [user])

    def setup_db(self, tag):
        d = mkdtemp()
        check_output(['git', 'clone', '--branch', tag, '.', d], stderr=subprocess.DEVNULL)
        check_output(['./misc/sample.py', '--redis-url=15'], stderr=subprocess.DEVNULL, cwd=d)

class EditableTest(MeetlingTestCase):
    def test_edit(self):
        cat = Cat(id='Cat', app=self.app, authors=[], name=None)
        cat.edit(name='Happy')
        cat.edit(name='Grumpy')
        user2 = self.app.login()
        cat.edit(name='Hover')
        self.assertEqual(cat.authors, [self.user, user2])

class UserTest(MeetlingTestCase):
    def test_edit(self):
        self.user.edit(name='Happy')
        self.assertEqual(self.user.name, 'Happy')

class SettingsTest(MeetlingTestCase):
    def test_edit(self):
        self.app.user = self.staff_member
        settings = self.app.settings
        settings.edit(title='Cat Meetling', icon='http://example.org/static/icon.svg')
        self.assertEqual(settings.title, 'Cat Meetling')
        self.assertEqual(settings.icon, 'http://example.org/static/icon.svg')
        self.assertIsNone(settings.favicon)

class MeetingTest(MeetlingTestCase):
    def setUp(self):
        super().setUp()
        self.meeting = self.app.create_meeting('Cat hangout')

    def test_edit(self):
        self.meeting.edit(title='Awesome cat hangout')
        self.assertEqual(self.meeting.title, 'Awesome cat hangout')
        self.assertIsNone(self.meeting.description)

    def test_create_agenda_item(self):
        item = self.meeting.create_agenda_item('Purring')
        self.assertIn(item.id, self.meeting.items)

class AgendaItemTest(MeetlingTestCase):
    def test_edit(self):
        meeting = self.app.create_meeting('Cat Hangout')
        item = meeting.create_agenda_item('Purring')
        item.edit(title='Intensive purring')
        self.assertEqual(item.title, 'Intensive purring')
        self.assertIsNone(item.description)

class Cat(Object, Editable):
    def __init__(self, id, app, authors, name):
        super().__init__(id=id, app=app)
        Editable.__init__(self, authors=authors)
        self.name = name

    def do_edit(self, **attrs):
        if 'name' in attrs:
            self.name = attrs['name']

    def json(self, include_users=False):
        json = super().json({'name': self.name})
        json.update(Editable.json(self, include_users))
        return json
