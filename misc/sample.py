#!/usr/bin/env python3

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

import sys
sys.path.insert(0, '.')

import argparse
from argparse import ArgumentParser
from meetling import Meetling

def main(args):
    parser = ArgumentParser(
        description=
            """Set up some sample data for Meetling, convenient for developing and experimenting.

            Warning: All existing data in the database will be deleted!
            """,
        argument_default=argparse.SUPPRESS)
    parser.add_argument('--redis-url',
                        help='See python3 -m meetling --redis-url command line option.')
    args = parser.parse_args(args[1:])

    app = Meetling(**vars(args))
    app.r.flushdb()
    app.update()

    staff_member = app.login()
    staff_member.edit(name='Ceiling')
    app.settings.edit(title='Meetling Lab')
    user = app.login()
    user.edit(name='Happy')
    meeting1 = app.create_example_meeting()
    meeting2 = app.create_meeting('Cat hangout')
    meeting2.create_agenda_item('Eating')
    meeting2.create_agenda_item('Purring', duration=10, description='No snooping!')
    meeting2.trash_agenda_item(meeting2.create_agenda_item('Eatzing'))
    meeting2.trash_agenda_item(meeting2.create_agenda_item('Purring', duration=10,
                                                           description='No snoopzing!'))

    text = [
        'To log in as staff member, visit:',
        '',
        'http://localhost:8080/?login={}'.format(staff_member.auth_secret),
        '',
        'Meetings:',
        ''
    ]
    for meeting in [meeting1, meeting2]:
        text.append('* {}: http://localhost:8080/meetings/{}'.format(meeting.title, meeting.id))

    print('\n'.join(text))
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
