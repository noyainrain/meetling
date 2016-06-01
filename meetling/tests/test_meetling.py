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

from datetime import datetime
import os
import subprocess
from subprocess import check_output
from tempfile import mkdtemp

import micro
from tornado.testing import AsyncTestCase

from meetling import Meetling

class MeetlingTestCase(AsyncTestCase):
    def setUp(self):
        super().setUp()
        self.app = Meetling(redis_url='15')
        self.app.r.flushdb()
        self.app.update()
        self.staff_member = self.app.login()
        self.user = self.app.login()

class MeetlingTest(MeetlingTestCase):
    def test_create_meeting(self):
        meeting = self.app.create_meeting('Cat Hangout', description='  ')
        self.assertIn(meeting.id, self.app.meetings)
        # Whitespace-only strings should be converted to None
        self.assertIsNone(meeting.description)

    def test_create_meeting_title_empty(self):
        with self.assertRaises(micro.InputError):
            self.app.create_meeting('  ')

    def test_create_example_meeting(self):
        meeting = self.app.create_example_meeting()
        self.assertTrue(len(meeting.items))

class MeetlingUpdateTest(AsyncTestCase):
    @staticmethod
    def setup_db(tag):
        d = mkdtemp()
        check_output(['git', 'clone', '--branch', tag, '.', d], stderr=subprocess.DEVNULL)

        # Compatibility for misc/sample.py (obsolete since 0.9.4)
        if os.path.isfile(os.path.join(d, 'misc/sample.py')):
            check_output(['./misc/sample.py', '--redis-url=15'], stderr=subprocess.DEVNULL, cwd=d)
            return

        check_output(['make', 'sample', 'REDISURL=15'], stderr=subprocess.DEVNULL, cwd=d)

    def test_update_db_fresh(self):
        app = Meetling(redis_url='15')
        app.r.flushdb()
        app.update()
        self.assertEqual(app.settings.title, 'My Meetling')

    def test_update_db_version_previous(self):
        self.setup_db('0.8.2')
        app = Meetling(redis_url='15')
        app.update()

        settings = app.settings
        user = settings.staff[0]
        meeting = next(m for m in app.meetings.values() if m.title == 'Cat hangout')
        item = list(meeting.items.values())[0]
        self.assertFalse(settings.trashed)
        self.assertFalse(user.trashed)
        self.assertFalse(meeting.trashed)
        self.assertFalse(item.trashed)

    def test_update_db_version_first(self):
        self.setup_db('0.5.0')
        app = Meetling(redis_url='15')
        app.update()

        settings = app.settings
        user = settings.staff[0]
        meeting = next(m for m in app.meetings.values() if m.title == 'Cat hangout')
        item = list(meeting.items.values())[0]
        # update to version 2
        self.assertEqual(user.name, 'Guest')
        self.assertEqual(user.authors, [user])
        # update to version 3
        self.assertIsNone(meeting.time)
        self.assertIsNone(meeting.location)
        self.assertIsNone(item.duration)
        # update to version 4
        self.assertFalse(settings.trashed)
        self.assertFalse(user.trashed)
        self.assertFalse(meeting.trashed)
        self.assertFalse(item.trashed)

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
        self.items = [
            self.meeting.create_agenda_item('Eating'),
            self.meeting.create_agenda_item('Purring'),
            self.meeting.create_agenda_item('Sleeping')
        ]
        self.external_item = self.app.create_meeting('Other').create_agenda_item('Other')

    def test_edit(self):
        time = datetime.utcnow()
        self.meeting.edit(title='Awesome cat hangout', time=time)
        self.assertEqual(self.meeting.title, 'Awesome cat hangout')
        self.assertEqual(self.meeting.time, time)
        self.assertIsNone(self.meeting.description)

    def test_create_agenda_item(self):
        # create_agenda_item() called by setUp()
        self.assertEqual(list(self.meeting.items.values()), self.items)

    def test_trash_agenda_item(self):
        self.meeting.trash_agenda_item(self.items[0])
        self.assertEqual(list(self.meeting.items.values()), self.items[1:])
        self.assertEqual(list(self.meeting.trashed_items.values()), [self.items[0]])

    def test_trash_agenda_item_item_trashed(self):
        self.meeting.trash_agenda_item(self.items[0])
        with self.assertRaisesRegex(micro.ValueError, 'item_not_found'):
            self.meeting.trash_agenda_item(self.items[0])

    def test_restore_agenda_item(self):
        self.meeting.trash_agenda_item(self.items[0])
        self.meeting.restore_agenda_item(self.items[0])
        self.assertEqual(list(self.meeting.items.values()), self.items[1:] + [self.items[0]])
        self.assertFalse(list(self.meeting.trashed_items.values()))

    def test_restore_agenda_item_item_not_trashed(self):
        with self.assertRaisesRegex(micro.ValueError, 'item_not_found'):
            self.meeting.restore_agenda_item(self.items[0])

    def test_move_agenda_item(self):
        self.meeting.move_agenda_item(self.items[1], self.items[2])
        self.assertEqual(list(self.meeting.items.values()),
                         [self.items[0], self.items[2], self.items[1]])

    def test_move_agenda_item_to_none(self):
        self.meeting.move_agenda_item(self.items[1], None)
        self.assertEqual(list(self.meeting.items.values()),
                         [self.items[1], self.items[0], self.items[2]])

    def test_move_agenda_item_to_item(self):
        self.meeting.move_agenda_item(self.items[1], self.items[1])
        self.assertEqual(list(self.meeting.items.values()), self.items)

    def test_move_agenda_item_item_external(self):
        with self.assertRaisesRegex(micro.ValueError, 'item_not_found'):
            self.meeting.move_agenda_item(self.external_item, None)

    def test_move_agenda_item_to_external(self):
        with self.assertRaisesRegex(micro.ValueError, 'to_not_found'):
            self.meeting.move_agenda_item(self.items[0], self.external_item)

class AgendaItemTest(MeetlingTestCase):
    def test_edit(self):
        meeting = self.app.create_meeting('Cat Hangout')
        item = meeting.create_agenda_item('Purring')
        item.edit(title='Intensive purring', duration=10)
        self.assertEqual(item.title, 'Intensive purring')
        self.assertEqual(item.duration, 10)
        self.assertIsNone(item.description)
