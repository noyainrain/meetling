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

from redis import RedisError
from tornado.testing import AsyncTestCase

import micro
from micro import Application, Object, Editable, Settings, Feed, Event

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
        app = CatApp(redis_url='//localhoax')
        with self.assertRaises(RedisError):
            app.login()

    def test_login_code(self):
        user = self.app.login(code=self.staff_member.auth_secret)
        self.assertEqual(user, self.staff_member)

    def test_login_code_invalid(self):
        with self.assertRaisesRegex(micro.ValueError, 'code_invalid'):
            self.app.login(code='foo')

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

class FeedTest(MicroTestCase):
    def setUp(self):
        super().setUp()
        self.feed = Feed(id='Feed', trashed=False, app=self.app, subscribers=[])

    def test_publish_event(self):
        called = []
        def _foo(event, user, feed):
            called.append((event, user, feed))
        self.app.handle_notification = _foo

        # Subscribe as user and staff member
        self.feed.subscribe()
        self.app.user = self.staff_member
        self.feed.subscribe()

        event = Event('FeedTest.test_publish_event', self, self.user)
        self.feed.publish_event(event)
        self.assertEqual(called, [(event, self.staff_member, self.feed)])

    def test_subscribe(self):
        self.feed.subscribe()
        self.assertIn(self.user, self.feed.subscribers)

    def test_subscribe_already(self):
        # TODO
        self.feed.subscribe()
        with self.assertRaisesRegex(ValueError, '.*'):
            self.feed.subscribe()

    def test_unsubscribe(self):
        self.feed.subscribe()
        self.feed.unsubscribe()
        self.assertNotIn(self.user, self.feed.subscribers)

    def test_unsubscribe_not(self):
        # TODO
        with self.assertRaisesRegex(ValueError, '.*'):
            self.feed.unsubscribe()

class CatApp(Application):
    def __init__(self, redis_url=''):
        super().__init__(redis_url=redis_url)
        self.types.update({'Cat': Cat})

    def update(self):
        settings = Settings(id='Settings', trashed=False, app=self, authors=[], title='CatApp',
                            icon=None, favicon=None, staff=[])
        self.r.oset(settings.id, settings)

class Cat(Object, Editable):
    def __init__(self, id, trashed, app, authors, name):
        super().__init__(id=id, trashed=trashed, app=app)
        Editable.__init__(self, authors=authors)
        self.name = name

    def do_edit(self, **attrs):
        if 'name' in attrs:
            self.name = attrs['name']

    def json(self, restricted=False, include_users=False):
        json = super().json(attrs={'name': self.name})
        json.update(Editable.json(self, restricted=restricted, include_users=include_users))
        return json
