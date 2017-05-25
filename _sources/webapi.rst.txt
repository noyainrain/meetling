Web API
=======

Introduction
------------

Meetling provides a JSON REST API.

Arguments are passed to an endpoint simply as JSON object and the result is returned as JSON value.
*Objects* contain a ``__type__`` attribute that holds the name of the object type.

If a requested endpoint doesn't exist, a :ref:`NotFoundError` is returned. For any endpoint, an
:ref:`InputError` is returned if the input contains invalid arguments.

Authentication and Permissions
------------------------------

To make an API request authenticated as some user, include a cookie named ``auth_secret`` with the
:ref:`User` 's *auth_secret*.

If user authentication with the given secret fails, an :ref:`AuthenticationError` is returned. For
any endpoint, a :ref:`PermissionError` is returned if the current user is not allowed to perform the
action.

Lists
-----

For most API endpoints which return a list, a slice of the form ``/(start):(stop)`` may be appended
to the URL, where *start* (inclusive) and *stop* (exclusive) are indices of the items to return.
The maximum number of items is limited to a *limit* of ``100``. Both *start* and *stop* are optional
and default to ``0`` and ``start + limit`` respectively.

Example: ``/api/activity`` (which is equivalent to ``/api/activity/:`` or ``/api/activity/0:100``)
returns the first hundred items (i.e. global events) and ``/api/activity/10:20`` returns the items
from index 10 up to including 19.

Additional types
----------------

A *polyglot string* is an :class:`Object` holding multiple translations of a string indexed by short
language tag.

Usage examples
--------------

A new :ref:`User` is created and logged in with the following request::

    $ curl -d "" https://meetling.org/api/login
    {
        "__type__": "User",
        "id": "abcd",
        "auth_secret": "wxyz",
        ...
    }

To authenticate further API calls, the returned *auth_secret* is set as cookie.

Setting a user's *email* address requires multiple steps. First::

    $ curl -b "auth_secret=wxyz" -d '{"email": "happy@example.org"}' \
           https://meetling.org/api/users/abcd/set-email
    {
        "__type__": "AuthRequest",
        "id": "efgh"
    }

This triggers a third party authentication via the email provider (as layed out in
:ref:`AuthRequest`). The resulting authentication code (here ``stuv``) is then verified to finish
setting the email address::

    $ curl -b "auth_secret=wxyz" -d '{"auth_request_id": "efgh", "auth": "stuv"}' \
           https://meetling.org/api/users/abcd/finish-set-email
    {
        "__type__": "User",
        "id": "abcd",
        "email": "happy@example.org",
        ...
    }

.. _Application:

Application
-----------

Social micro web app.

.. http:get:: /api/activity

   Global :ref:`Activity` feed.

.. http:post:: /api/login

   ``{"code": null}``

   Log in an :ref:`User` (device) and return them.

   If *code* is given, log in an existing user with the login *code*. If the login fails, a
   :exc:`ValueError` (``code_invalid``) is returned.

   If *code* is ``null``, create and log in a new user. The very first user who logs in is
   registered as staff member.

.. _AuthRequest:

AuthRequest
-----------

Third party authentication request.

To set an :ref:`User` 's email address, a third party authentication via the email provider is
performed to proof ownership over the address: First an email message containing a secret
authentication code is sent to the user. The email provider authenticates the user by login to their
mailbox, where they retrieve the code. Finally the code is passed back to and verified by the
application.

AuthRequest is an :ref:`Object`.

.. _Meetling:

Meetling
--------

Meetling :ref:`Application`.

.. http:post:: /api/meetings

   ``{"title", "time": null, "location": null, "description": null}``

   Create a :ref:`Meeting` and return it.

   Permission: Authenticated users.

.. http:post:: /api/create-example-meeting

   Create a :ref:`Meeting` with an example agenda and return it.

   Useful to illustrate how meetings work.

   Permission: Authenticated users.

.. _Object:

Object
------

Object in the application universe.

.. attribute:: id

   Unique ID of the object.

.. attribute:: trashed

   Indicates if the object has been trashed (deleted).

.. _Editable:

Editable
--------

:ref:`Object` that can be edited.

The URL that uniquely identifies an object is referred to as *object-url*, e.g. ``meetings/abc`` for
a :ref:`Meeting` with the *id* ``abc``.

.. describe:: authors

   :ref:`User` s who edited the object.

.. http:post:: /api/(object-url)

   ``{attrs...}``

   Edit the attributes given by *attrs* and return the updated object.

   A *trashed* (deleted) object cannot be edited. In this case a :ref:`ValueError`
   (`object_trashed`) is returned.

   Permission: Authenticated users.

.. _User:

User
----

User is an :ref:`Object` and :ref:`Editable` by the user oneself.

.. describe:: name

   Name or nick name.

.. describe:: email

   Email address, being a single line string. May be ``None``. Visible only to the user oneself.

.. describe:: auth_secret

   Secret for authentication. Visible only to the user oneself.

.. http:get:: /api/users/(id)

   Get the user given by *id*.

.. http:post:: /api/users/(id)/set-email

   {"email"}

   Start to set the user's *email* address.

   A third party authentication via the email provider (as layed out in :ref:`AuthRequest`) is
   triggered and a corresponding :ref:`AuthRequest` is returned. To finish setting the email address
   use :http:post:`/api/users/(id)/finish-set-email`.

   Permission: The user oneself.

.. http:post:: /api/users/(id)/finish-set-email

   {"auth_request_id", "auth"}

   Finish setting the user's *email* address and return the user.

   *auth* is the authentication code, resulting from the :ref:`AuthRequest` with *auth_request_id*,
   to be verified. If the verification fails, a :ref:`ValueError` (``auth_invalid``) is returned. If
   the given email address is already associated with another user, a :ref:`ValueError`
   (``email_duplicate``) is returned.

   Permission: The user oneself.

.. http:post:: /api/users/(id)/remove-email

   Remove the user's current *email* address and return the user.

   If the user's *email* is not set, a :ref:`ValueError` (``user_no_email``) is returned.

   Permission: The user oneself.

.. _Settings:

Settings
--------

App settings.

Settings is an :ref:`Object` and :ref:`Editable` by staff members.

.. describe:: title

   Site title.

.. describe:: icon

   URL of the site icon. May be ``null``.

.. describe:: favicon

   URL of the site icon optimized for a small size. May be ``null``.

.. describe:: provider_name

   Service provider name. May be ``null``.

.. describe:: provider_url

   URL of the website of the service provider. May be ``null``.

.. describe:: provider_description

   Short polyglot description of the service provider, which can be read as an addendum to the
   *provider_name*.

.. describe:: feedback_url

   URL of the feedback site / help desk. May be ``null``.

.. describe:: staff

   Staff users.

.. http:get:: /api/settings

   Get the settings.

.. _Activity:

Activity
--------

Activity feed (of events) around a common topic/context.

*activity-url* is the URL that identifies the activity feed, e.g. ``/api/activity``.

.. http:get:: (activity-url)

   Get the list of recorded :ref:`Event` s.

.. _Event:

Event
-----

Event about an action on an *object* by an *user*.

Event is an :ref:`Object`.

.. attribute:: type

   Type of the event.

.. attribute:: object

   :ref:`Object` for which the event happened. ``null`` if it is a global event.

.. attribute:: user

   :ref:`User` who triggered the event.

.. describe:: time

   Date and time at which the event happened.

.. attribute:: detail

   Dictionary with additonal details about the event. The contents depend on the event *type*.

.. _Meeting:

Meeting
-------

Meeting.

Meeting is an :ref:`Object` and :ref:`Editable`.

.. describe:: title

   Title of the meeting.

.. describe:: time

   Date and time the meeting begins. May be ``null``.

.. describe:: location

   Location where the meeting takes place. May be ``null``.

.. describe:: description

   Description of the meeting. May be ``null``.

.. http:get:: /api/meetings/(id)

   Get the meeting given by *id*.

.. http:get:: /api/meetings/(id)/items

   Get the list of :ref:`AgendaItem` s on the meeting's agenda.

   If ``/trashed`` is appended to the URL, only trashed (deleted) items are returned.

.. http:post:: /api/meetings/(id)/items

   ``{"title", "duration": null, "description": null}``

   Create an :ref:`AgendaItem` and return it.

   Permission: Authenticated users.

.. http:post:: /api/meetings/(id)/trash-agenda-item

   ``{"item_id"}``

   Trash (delete) the :ref:`AgendaItem` with *item_id*.

   If there is no item with *item_id* for the meeting, a :ref:`ValueError` (``item_not_found``) is
   returned.

   Permission: Authenticated users.

.. http:post:: /api/meetings/(id)/restore-agenda-item

   ``{"item_id"}``

   Restore the previously trashed (deleted) :ref:`AgendaItem` with *item_id*.

   If there is no trashed item with *item_id* for the meeting, a :ref:`ValueError`
   (``item_not_found``) is returned.

   Permission: Authenticated users.

.. http:post:: /api/meetings/(id)/move-agenda-item

   ``{"item_id", "to_id"}``

   Move the :ref:`AgendaItem` with *item_id* to the position directly after the item with *to_id*.

   If *to_id* is ``null``, move the item to the top of the agenda.

   If there is no item with *item_id* or *to_id* for the meeting, a :ref:`ValueError`
   (``item_not_found`` or ``to_not_found``) is returned.

   Permission: Authenticated users.

.. _AgendaItem:

AgendaItem
----------

Item on a :ref:`Meeting` 's agenda.

AgendaItem is an :ref:`Object` and :ref:`Editable`.

.. describe:: title

   Title of the item.

.. describe:: duration

   Time the agenda item takes in minutes. May be ``null``.

.. describe:: description

   Description of the item. May be ``null``.

.. http:get:: /api/meetings/(meeting-id)/items/(item-id)

   Get the item given by *item-id*.

.. _ValueError:

ValueError
----------

Returned for value-related errors.

.. attribute:: code

   Error string providing more information about the problem.

.. _InputError:

InputError
----------

Returned if the input to an endpoint contains one or more arguments with an invalid value.

InputError is a :ref:`ValueError` with *code* set to ``input_invalid``.

.. attribute:: errors

   Map of argument names / error strings for every problematic argument of the input.

.. _NotFoundError:

NotFoundError
-------------

Returned if a requested endpoint does not exist.

.. _AuthenticationError:

AuthenticationError
-------------------

Returned if user authentication fails.

.. _PermissionError:

PermissionError
---------------

Returned if the current user is not allowed to perform an action.
