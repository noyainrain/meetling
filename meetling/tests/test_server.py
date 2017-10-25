# Meetling
# Copyright (C) 2017 Meetling contributors
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

from micro.test import ServerTestCase
from tornado.httpclient import HTTPError
from tornado.testing import gen_test

from meetling.server import make_server

class MeetlingServerTest(ServerTestCase):
    def setUp(self):
        super().setUp()
        self.server = make_server(port=16160, redis_url='15')
        app = self.server.app
        app.r.flushdb()
        self.server.start()
        self.user = app.login()
        self.meeting = app.create_meeting('Cat hangout')
        self.item = self.meeting.create_agenda_item('Eating')
        self.client_user = self.user

    @gen_test
    def test_availability(self):
        now = datetime.utcnow()
        yield self.request('/api/meetings', method='POST',
                           body='{"title": "Cat hangout", "description": "  "}')
        yield self.request('/api/create-example-meeting', method='POST', body='')
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

    @gen_test
    def test_post_meeting_trash_agenda_item_item_id_nonexistent(self):
        with self.assertRaises(HTTPError) as cm:
            yield self.request('/api/meetings/{}/trash-agenda-item'.format(self.meeting.id),
                               method='POST', body='{"item_id": "foo"}')
        self.assertEqual(cm.exception.code, http.client.BAD_REQUEST)
        error = json.loads(cm.exception.response.body.decode())
        self.assertEqual(error.get('__type__'), 'ValueError')
