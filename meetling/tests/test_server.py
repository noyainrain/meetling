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
import http.client
import json
from urllib.parse import urljoin

from tornado.httpclient import AsyncHTTPClient, HTTPError
from tornado.testing import AsyncTestCase, gen_test

from meetling.server import MeetlingServer

class MeetlingServerTest(AsyncTestCase):
    def setUp(self):
        super().setUp()
        self.server = MeetlingServer(redis_url='15')
        self.server.listen(16160, 'localhost')

        app = self.server.app
        app.r.flushdb()
        app.update()
        self.staff_member = app.login()
        self.user = app.login()
        self.meeting = self.server.app.create_meeting('Cat hangout')
        self.item = self.meeting.create_agenda_item('Eating')

        self.client_user = self.user

    def request(self, url, **args):
        headers = args.pop('headers', {})
        if self.client_user:
            headers.update({'Cookie': 'auth_secret=' + self.client_user.auth_secret})
        return AsyncHTTPClient().fetch(urljoin('http://localhost:16160/', url), headers=headers,
                                       **args)

    @gen_test
    def test_availability(self):
        # UI
        yield self.request('/')
        yield self.request(
            '/log-client-error', method='POST',
            body='{"type": "Error", "stack": "meetling.Page.prototype.createdCallback", "url": "/"}')
        yield self.request('/replace-auth', method='POST', body='')

        # API
        now = datetime.utcnow()
        yield self.request('/api/login', method='POST', body='')
        yield self.request('/api/meetings', method='POST',
                           body='{"title": "Cat hangout", "description": "  "}')
        yield self.request('/api/create-example-meeting', method='POST', body='')
        yield self.request('/api/users/' + self.user.id)
        yield self.request('/api/users/' + self.user.id, method='POST', body='{"name": "Happy"}')
        yield self.request('/api/settings')
        yield self.request('/api/meetings/' + self.meeting.id)
        yield self.request(
            '/api/meetings/' + self.meeting.id, method='POST',
            body='{{"title": "Awesome cat hangout", "time": "{}Z"}}'.format(now.isoformat()))
        yield self.request('/api/meetings/{}/items'.format(self.meeting.id))
        yield self.request('/api/meetings/{}/items'.format(self.meeting.id), method='POST',
                           body='{"title": "Purring"}')
        yield self.request('/api/meetings/{}/items/trashed'.format(self.meeting.id))
        yield self.request('/api/meetings/{}/trash-agenda-item'.format(self.meeting.id),
                           method='POST', body='{{"item_id": "{}"}}'.format(self.item.id))
        yield self.request('/api/meetings/{}/restore-agenda-item'.format(self.meeting.id),
                           method='POST', body='{{"item_id": "{}"}}'.format(self.item.id))
        yield self.request(
            '/api/meetings/{}/move-agenda-item'.format(self.meeting.id), method='POST',
            body='{{"item_id": "{}", "to_id": null}}'.format(self.item.id))
        yield self.request('/api/meetings/{}/items/{}'.format(self.meeting.id, self.item.id))
        yield self.request('/api/meetings/{}/items/{}'.format(self.meeting.id, self.item.id),
                           method='POST', body='{"title": "Intensive purring", "duration": 10}')
        yield self.request(
            '/api/meetings/{}/items/{}/comments'.format(self.meeting.id, self.item.id))
        yield self.request(
            '/api/meetings/{}/items/{}/comments'.format(self.meeting.id, self.item.id),
            method='POST', body='{"text": "foobar"}')

        # API (as staff member)
        self.client_user = self.staff_member
        yield self.request(
            '/api/settings', method='POST',
            body='{"title": "Cat Meetling", "icon": "http://example.org/static/icon.svg"}')

    @gen_test
    def test_get_meeting(self):
        response = yield self.request('/api/meetings/' + self.meeting.id)
        meeting = json.loads(response.body.decode())
        self.assertEqual(meeting.get('__type__'), 'Meeting')

    @gen_test
    def test_get_meeting_id_nonexistent(self):
        with self.assertRaises(HTTPError) as cm:
            yield self.request('/api/meetings/foo')
        self.assertEqual(cm.exception.code, http.client.NOT_FOUND)

    @gen_test
    def test_post_meeting_description_bad_type(self):
        with self.assertRaises(HTTPError) as cm:
            yield self.request('/api/meetings/' + self.meeting.id, method='POST',
                               body='{"description": 42}')
        self.assertEqual(cm.exception.code, http.client.BAD_REQUEST)
        error = json.loads(cm.exception.response.body.decode())
        self.assertEqual(error.get('__type__'), 'InputError')

    @gen_test
    def test_post_meeting_trash_agenda_item_item_id_nonexistent(self):
        with self.assertRaises(HTTPError) as cm:
            yield self.request('/api/meetings/{}/trash-agenda-item'.format(self.meeting.id),
                               method='POST', body='{"item_id": "foo"}')
        self.assertEqual(cm.exception.code, http.client.BAD_REQUEST)
        error = json.loads(cm.exception.response.body.decode())
        self.assertEqual(error.get('__type__'), 'ValueError')

    @gen_test
    def test_post_body_invalid_json(self):
        with self.assertRaises(HTTPError) as cm:
            yield self.request('/api/meetings/' + self.meeting.id, method='POST', body='foo')
        e = cm.exception
        self.assertEqual(e.code, http.client.BAD_REQUEST)
