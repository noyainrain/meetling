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

"""Core parts of Meetling."""

from datetime import datetime, timedelta
from itertools import chain

from micro import (Application, Object, Editable, Settings, Feed, Event, ValueError, InputError,
                   PermissionError)
from micro.jsonredis import JSONRedis, JSONRedisMapping
from micro.util import parse_isotime, randstr, str_or_none

class Meetling(Application):
    """See :ref:`Meetling`.

    .. attribute:: meetings

       Map of all :class:`Meeting` s.
    """

    def __init__(self, redis_url='', email='bot@localhost', smtp_url='',
                 render_email_auth_message=None):
        super().__init__(redis_url=redis_url, email=email, smtp_url=smtp_url,
                         render_email_auth_message=render_email_auth_message)
        def _meeting(time, **kwargs):
            return Meeting(time=parse_isotime(time) if time else time, **kwargs)
        self.types.update({'Meeting': _meeting, 'AgendaItem': AgendaItem})
        self.meetings = JSONRedisMapping(self.r, 'meetings')

    def update(self):
        db_version = self.r.get('version')
        if not db_version:
            settings = Settings(id='Settings', trashed=False, app=self, authors=[],
                                title='My Meetling', icon=None, favicon=None, staff=[])
            self.r.oset(settings.id, settings)
            self.r.set('version', 5)
            return

        db_version = int(db_version)
        # JSONRedis without en-/decoding and caching
        r = JSONRedis(self.r.r)
        r.caching = False

        if db_version < 2:
            users = r.omget(r.lrange('users', 0, -1))
            for user in users:
                user['name'] = 'Guest'
                user['authors'] = [user['id']]
            r.omset({u['id']: u for u in users})
            r.set('version', 2)

        if db_version < 3:
            meetings = r.omget(r.lrange('meetings', 0, -1))
            for meeting in meetings:
                meeting['time'] = None
                meeting['location'] = None

                items = r.omget(r.lrange(meeting['id'] + '.items', 0, -1))
                for item in items:
                    item['duration'] = None
                r.omset({i['id']: i for i in items})
            r.omset({m['id']: m for m in meetings})
            r.set('version', 3)

        if db_version < 4:
            meeting_ids = r.lrange('meetings', 0, -1)
            objects = r.omget(chain(
                ['Settings'],
                r.lrange('users', 0, -1),
                meeting_ids,
                chain.from_iterable(r.lrange(i + b'.items', 0, -1) for i in meeting_ids)
            ))
            for object in objects:
                object['trashed'] = False
            r.omset({o['id']: o for o in objects})
            r.set('version', 4)

        if db_version < 5:
            users = r.omget(r.lrange('users', 0, -1))
            for user in users:
                user['email'] = None
            r.omset({u['id']: u for u in users})
            r.set('version', 5)

        if db_version < 6:
            meetings = r.omget(r.lrange('meetings', 0, -1))
            for meeting in meetings:
                meeting['subscribers'] = []
                items = r.omget(r.lrange(meeting['id'] + '.items', 0, -1) +
                                r.lrange(meeting['id'] + '.trashed_items', 0, -1))
                for item in items:
                    item['meeting'] = meeting['id']
                r.omset({i['id']: i for i in items})
            r.omset({m['id']: m for m in meetings})
            r.set('version', 6)

    def create_meeting(self, title, time=None, location=None, description=None):
        """See :http:post:`/api/meetings`."""
        if not self.user:
            raise PermissionError()

        e = InputError()
        if not str_or_none(title):
            e.errors['title'] = 'empty'
        e.trigger()

        meeting = Meeting(
            id='Meeting:' + randstr(), trashed=False, app=self, authors=[self.user.id],
            subscribers=[self.user.id], title=title, time=time, location=str_or_none(location),
            description=str_or_none(description))
        self.r.oset(meeting.id, meeting)
        self.r.rpush('meetings', meeting.id)
        return meeting

    def create_example_meeting(self):
        """See :http:post:`/api/create-example-meeting`."""
        if not self.user:
            raise PermissionError()

        time = (datetime.utcnow() + timedelta(days=7)).replace(hour=12, minute=0, second=0,
                                                               microsecond=0)
        meeting = self.create_meeting('Working group meeting', time, 'At the office',
                                      'We meet and discuss important issues.')
        meeting.create_agenda_item('Round of introductions')
        meeting.create_agenda_item('Lunch poll', duration=30,
                                   description='What will we have for lunch today?')
        meeting.create_agenda_item('Next meeting', duration=5,
                                   description='When and where will our next meeting be?')
        return meeting

class Meeting(Feed, Editable):
    """See :ref:`Meeting`.

    .. attribute:: items

       Ordered map of :class:`AgendaItem` s on the meeting's agenda.

    .. attribute:: trashed_items

       Ordered map of trashed (deleted) :class:`AgendaItem` s.
    """

    def __init__(self, id, trashed, app, subscribers, authors, title, time, location, description):
        super().__init__(id=id, trashed=trashed, app=app, subscribers=subscribers)
        Editable.__init__(self, authors=authors, feed=self)
        self.title = title
        self.time = time
        self.location = location
        self.description = description

        self._items_key = self.id + '.items'
        self._trashed_items_key = self.id + '.trashed_items'
        self.items = JSONRedisMapping(self.app.r, self._items_key)
        self.trashed_items = JSONRedisMapping(self.app.r, self._trashed_items_key)

    def do_edit(self, **attrs):
        e = InputError()
        if 'title' in attrs and not str_or_none(attrs['title']):
            e.errors['title'] = 'empty'
        e.trigger()

        if 'title' in attrs:
            self.title = attrs['title']
        if 'time' in attrs:
            self.time = attrs['time']
        if 'location' in attrs:
            self.location = str_or_none(attrs['location'])
        if 'description' in attrs:
            self.description = str_or_none(attrs['description'])

    def create_agenda_item(self, title, duration=None, description=None):
        """See :http:post:`/api/meetings/(id)/items`."""
        if not self.app.user:
            raise PermissionError()

        e = InputError()
        if str_or_none(title) is None:
            e.errors['title'] = 'empty'
        if duration is not None and duration <= 0:
            e.errors['duration'] = 'not_positive'
        description = str_or_none(description)
        e.trigger()

        item = AgendaItem(
            id='AgendaItem:' + randstr(), trashed=False, app=self.app, authors=[self.app.user.id],
            title=title, duration=duration, description=description, meeting=self.id)
        self.app.r.oset(item.id, item)
        self.app.r.rpush(self._items_key, item.id)

        self.publish_event(Event('meeting-create-agenda-item', self, self.app.user, {'item': item}))
        return item

    def trash_agenda_item(self, item):
        """See :http:post:`/api/meetings/(id)/trash-agenda-item`."""
        # TODO: doc
        if not self.app.user:
            raise PermissionError()

        if not self.app.r.lrem(self._items_key, 1, item.id):
            raise ValueError('item_not_found')
        self.app.r.rpush(self._trashed_items_key, item.id)
        item.trashed = True
        self.app.r.oset(item.id, item)

        self.publish_event(Event('meeting-trash-agenda-item', self, self.app.user, {'item': item}))

    def restore_agenda_item(self, item):
        """See :http:post:`/api/meetings/(id)/restore-agenda-item`."""
        # TODO: doc
        if not self.app.user:
            raise PermissionError()

        if not self.app.r.lrem(self._trashed_items_key, 1, item.id):
            raise ValueError('item_not_found')
        self.app.r.rpush(self._items_key, item.id)
        item.trashed = False
        self.app.r.oset(item.id, item)

        self.publish_event(Event('meeting-restore-agenda-item', self, self.app.user,
                                 {'item': item}))

    def move_agenda_item(self, item, to):
        """See :http:post:`/api/meetings/(id)/move-agenda-item`."""
        # TODO: doc
        if not self.app.user:
            raise PermissionError()

        if to:
            if to.id not in self.items:
                raise ValueError('to_not_found')
            if to == item:
                # No op
                return
        if not self.app.r.lrem(self._items_key, 1, item.id):
            raise ValueError('item_not_found')
        if to:
            self.app.r.linsert(self._items_key, 'after', to.id, item.id)
        else:
            self.app.r.lpush(self._items_key, item.id)

        # TODO: frm & to?
        # TODO: OQ: consolidate individual move events into a meeting-reorder/sort-agenda event?
        # maybe later?
        self.publish_event(Event('meeting-move-agenda-item', self, self.app.user, {'item': item}))

    def json(self, restricted=False, include_users=False, include_items=False):
        """See :meth:`Object.json`.

        If *include_items* is ``True``, *items* and *trashed_items* are included.
        """
        # pylint: disable=arguments-differ; extended signature
        json = super().json(restricted=restricted)
        json.update(Editable.json(self, restricted=restricted, include_users=include_users))
        json.update({
            'title': self.title,
            'time': self.time.isoformat() + 'Z' if self.time else None,
            'location': self.location,
            'description': self.description
        })
        if include_items:
            json['items'] = [i.json(restricted=restricted, include_users=include_users)
                             for i in self.items.values()]
            json['trashed_items'] = [i.json(restricted=restricted, include_users=include_users)
                                     for i in self.trashed_items.values()]
        return json

class AgendaItem(Object, Editable):
    """See :ref:`AgendaItem`."""

    def __init__(self, id, trashed, app, authors, title, duration, description, meeting):
        super().__init__(id=id, trashed=trashed, app=app)
        self.title = title
        self.duration = duration
        self.description = description
        self._meeting_id = meeting
        Editable.__init__(self, authors=authors, feed=self.meeting)

    @property
    def meeting(self):
        return self.app.r.oget(self._meeting_id)

    def do_edit(self, **attrs):
        e = InputError()
        if 'title' in attrs and str_or_none(attrs['title']) is None:
            e.errors['title'] = 'empty'
        if attrs.get('duration') is not None and attrs['duration'] <= 0:
            e.errors['duration'] = 'not_positive'
        e.trigger()

        if 'title' in attrs:
            self.title = attrs['title']
        if 'duration' in attrs:
            self.duration = attrs['duration']
        if 'description' in attrs:
            self.description = str_or_none(attrs['description'])

    def json(self, restricted=False, include_users=False):
        json = super().json(attrs={
            'title': self.title,
            'duration': self.duration,
            'description': self.description,
            'meeting': self._meeting_id
        })
        json.update(Editable.json(self, restricted=restricted, include_users=include_users))
        return json
