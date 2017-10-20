Web API
=======

.. include:: micro/general.inc

.. _Meetling:

Meetling
--------

Meetling application.

.. include:: micro/application-endpoints.inc

.. http:post:: /api/meetings

   ``{"title", "time": null, "location": null, "description": null}``

   Create a :ref:`Meeting` and return it.

   Permission: Authenticated users.

.. http:post:: /api/create-example-meeting

   Create a :ref:`Meeting` with an example agenda and return it.

   Useful to illustrate how meetings work.

   Permission: Authenticated users.

.. _Settings:

Settings
--------

App settings.

Settings is editable by staff members.

.. include:: micro/settings-attributes.inc

.. include:: micro/settings-endpoints.inc

.. _Meeting:

Meeting
-------

Meeting.

.. include:: micro/object-attributes.inc

.. include:: micro/editable-attributes.inc

.. describe:: title

   Title of the meeting.

.. describe:: time

   Date and time the meeting begins. May be ``null``.

.. describe:: location

   Location where the meeting takes place. May be ``null``.

.. describe:: description

   Description of the meeting. May be ``null``.

.. include:: micro/editable-endpoints.inc

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

.. include:: micro/object-attributes.inc

.. include:: micro/editable-attributes.inc

.. describe:: title

   Title of the item.

.. describe:: duration

   Time the agenda item takes in minutes. May be ``null``.

.. describe:: description

   Description of the item. May be ``null``.

.. http:get:: /api/meetings/(meeting-id)/items/(item-id)

   Get the item given by *item-id*.

.. include:: micro/editable-endpoints.inc
