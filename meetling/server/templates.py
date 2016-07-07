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

"""Server templates.

.. data:: MESSAGE_TEMPLATES

   TODO.
"""

MESSAGE_TEMPLATES = {
    'email_auth': """
        Subject: [{{ app.settings.title }}] Add email address

        Hi there!

        To add your email address {{ email }} to {{ app.settings.title }}, simply open this link:

        {{ server.url }}/user/edit#set-email={{ auth_request.id[12:] }}:{{ auth }}

        Or copy and paste the following code into the app:

        {{ auth }}

        ---

        If you did not request to add an email address to {{ app.settings.title }}, someone else may
        have entered your email address by mistake. In that case, please ignore this message, we
        will not bother you again.
    """

    'notification': """
        Subject: [{{ app.settings.title }}] {% block subject %}{% end %}

        Hi {{ user.name }}!

        {% block content %}{% end %}

        ---

        You received this notification because you are subscribed to updates about
        {% block feed-outline %}{% end %}. You can unsubscribe any time at:
        {{ server.url }}{% block feed-url %}{% end %}
    """,

    'editable-edit': """
        {% extends 'notification' %}
        {% block subject %}\
            {% set meeting = event.object.meeting if type(event.object).__name__ == 'AgendaItem' else event.object %}\
            {% if type(event.object).__name__ == 'Meeting' %}\
                "{{ meeting.title }}" edited\
            {% else %}\
                Agenda item of "{{ meeting.title }}" edited\
            {% end %}\
        {% end %}
        {% block content %}
            {% if type(event.object).__name__ == 'Meeting' %}
                "{{ meeting.title }}" was edited by {{ event.user.name }}.
            {% else %}
                The agenda item "{{ event.object.title }}" of "{{ meeting.title }}" was edited by
                {{ event.user.name }}.
            {% end %}

            For details, see: {{ server.url }}/meetings/{{ meeting.id }}
        {% end%}
        {% block feed-outline %}"{{ meeting.title }}"{% end %}
        {% block feed-url %}/meetings/{{ meeting.id }}{% end %}
    """,

    'meeting-create-agenda-item': """
        {% extends 'notification' %}
        {% block subject %}Agenda item proposed for "{{ event.object.title }}"{% end %}
        {% block content %}
            The new agenda item "{{ event.detail['item'].title }}" was proposed for
            "{{ event.object.title }}" by {{ event.user.name }}.

            For details, see: {{ server.url }}/meetings/{{ event.object.id }}
        {% end %}
        {% block feed-outline %}"{{ event.object.title }}"{% end %}
        {% block feed-url %}/meetings/{{ event.object.id }}{% end %}
    """,

    'meeting-trash-agenda-item': """
        {% extends 'notification' %}
        {% block subject %}Agenda item of "{{ event.object.title }}" trashed{% end %}
        {% block content %}
            The agenda item "{{ event.detail['item'].title }}" of "{{ event.object.title }}" was
            trashed by {{ event.user.name }}.

            For details, see: {{ server.url }}/meetings/{{ event.object.id }}
        {% end %}
        {% block feed-outline %}"{{ event.object.title }}"{% end %}
        {% block feed-url %}/meetings/{{ event.object.id }}{% end %}
    """,

    'meeting-restore-agenda-item': """
        {% extends 'notification' %}
        {% block subject %}Agenda item of "{{ event.object.title }}" restored{% end %}
        {% block content %}
            The agenda item "{{ event.detail['item'].title }}" of "{{ event.object.title }}" was
            restored by {{ event.user.name }}.

            For details, see: {{ server.url }}/meetings/{{ event.object.id }}
        {% end %}
        {% block feed-outline %}"{{ event.object.title }}"{% end %}
        {% block feed-url %}/meetings/{{ event.object.id }}{% end %}
    """,

    'meeting-move-agenda-item': """
        {% extends 'notification' %}
        {% block subject %}Agenda item of "{{ event.object.title }}" moved{% end %}
        {% block content %}
            The agenda item "{{ event.detail['item'].title }}" of "{{ event.object.title }}" was
            moved by {{ event.user.name }}.

            For details, see: {{ server.url }}/meetings/{{ event.object.id }}
        {% end %}
        {% block feed-outline %}"{{ event.object.title }}"{% end %}
        {% block feed-url %}/meetings/{{ event.object.id }}{% end %}
    """
}
