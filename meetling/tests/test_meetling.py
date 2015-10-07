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

from redis import RedisError
from tornado.testing import AsyncTestCase
from meetling import Meetling, InputError

class MeetlingTestCase(AsyncTestCase):
    def setUp(self):
        super().setUp()
        self.app = Meetling(redis_url='15')
        self.app.r.flushdb()
        self.app.update()

class MeetlingTest(MeetlingTestCase):
    def test_init_redis_url_invalid(self):
        with self.assertRaises(InputError):
            Meetling(redis_url='//localhost:foo')

    def test_create_meeting(self):
        meeting = self.app.create_meeting('Cat Hangout', '  ')
        self.assertIn(meeting.id, self.app.meetings)
        # Whitespace-only strings should be converted to None
        self.assertIsNone(meeting.description)

    def test_create_meeting_title_empty(self):
        with self.assertRaises(InputError):
            self.app.create_meeting('  ')

    def test_create_meeting_no_redis(self):
        app = Meetling(redis_url='//localhoax')
        with self.assertRaises(RedisError):
            app.create_meeting('Cat Hangout')

    def test_create_example_meeting(self):
        meeting = self.app.create_example_meeting()
        self.assertTrue(len(meeting.items))

class MeetlingUpdateTest(MeetlingTestCase):
    def test_update(self):
        # update() is called by setUp()
        self.assertEqual(self.app.settings.title, 'My Meetling')

class SettingsTest(MeetlingTestCase):
    def test_edit(self):
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
