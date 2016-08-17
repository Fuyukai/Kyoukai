.. py:currentmodule:: kyoukai

API Reference
=============

The following section outlines the API of Kyoukai, including some deeper parts that aren't covered by these docs.


Application Object
------------------

.. autoclass:: kyoukai.app.Kyoukai
	:members:


Blueprints
----------

.. autoclass:: kyoukai.blueprints.Blueprint
	:members:

Routes
------

.. autoclass:: kyoukai.route.Route
	:members:


HTTP Objects
------------

.. autoclass:: kyoukai.request.Request
	:members:

.. autoclass:: kyoukai.response.Response
	:members:

.. autoclass:: kyoukai.protocol.KyoukaiProtocol
	:members:

Asphalt
-------

These classes are for Asphalt usage, such as contexts.
You are not guaranteed to always have these specific objects.

.. autoclass:: kyoukai.context.HTTPRequestContext
	:members:

.. autoclass:: kyoukai.asphalt.KyoukaiComponent
	:members:

Views
-----

.. autoclass:: kyoukai.views.View
	:members:

.. automethod:: kyoukai.views.route
