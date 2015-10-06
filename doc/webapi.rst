Web API
=======

Introduction
------------

Meetling provides a JSON REST API.

Arguments are passed to an endpoint simply as JSON object and the result is returned as JSON value.
*Objects* contain a ``__type__`` attribute that holds the name of the object type.

For any endpoint an :ref:`InputError` is returned if the input contains invalid arguments.

.. _Meetling:

Meetling
--------

Meetling application.

.. http:post:: /api/login

   Log in a new :ref:`User` (device).

   A new user is created and returned.

.. http:post:: /api/meetings

   ``{"title", "description": null}``

   Create a :ref:`Meeting` with the given *title* and optional *description* and return it.

.. http:post:: /api/create-example-meeting

   Create a :ref:`Meeting` with an example agenda and return it.

   Useful to illustrate how meetings work.

.. _Editable:

Editable
--------

Object that can be edited.

The URL that uniquely identifies an object is referred to as *object-url*, e.g. ``meetings/abc`` for
a :ref:`Meeting` with the *id* ``abc``.

.. http:post:: /api/(object-url)

   ``{attrs...}``

   Edit the attributes given by *attrs* and return the updated object.

.. _User:

User
----

Meetling user.

.. describe:: id

   Unique ID of the user.

.. describe:: auth_secret

   Secret for authentication. Visible only to the user oneself.

.. http:get:: /api/users/(id)

   Get the user given by *id*.

.. _Settings:

Settings
--------

App settings.

Settings is :ref:`Editable`.

.. describe:: id

   Unique ID ``Settings``.

.. describe:: title

   Site title.

.. describe:: icon

   URL of the site icon. May be ``null``.

.. describe:: favicon

   URL of the site icon optimized for a small size. May be ``null``.

.. http:get:: /api/settings

   Get the settings.

.. _Meeting:

Meeting
-------

Meeting.

Meeting is :ref:`Editable`.

.. describe:: id

   Unique ID of the meeting.

.. describe:: title

   Title of the meeting.

.. describe:: description

   Description of the meeting. May be ``null``.

.. http:get:: /api/meetings/(id)

   Get the meeting given by *id*.

.. http:get:: /api/meetings/(id)/items

   Get the list of :ref:`AgendaItem` s on the meeting's agenda.

.. http:post:: /api/meetings/(id)/items

   ``{"title", "description": null}``

   Create an :ref:`AgendaItem` with the given *title* and optional *description* and return it.

.. _AgendaItem:

AgendaItem
----------

Item on a :ref:`Meeting` 's agenda.

AgendaItem is :ref:`Editable`.

.. describe:: id

   Unique ID of the item.

.. describe:: title

   Title of the item.

.. describe:: description

   Description of the item. May be ``null``.

.. http:get:: /api/meetings/(meeting-id)/items/(item-id)

   Get the item given by *item-id*.

.. _InputError:

InputError
----------

Returned if the input to an endpoint contains one or more arguments with an invalid value.

.. attribute:: errors

   Map of argument names / error strings for every problematic argument of the input.
