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

.. autoclass:: kyoukai.blueprint.Blueprint
	:members:

Routes
------

.. autoclass:: kyoukai.routes.Route
	:members:


HTTP Objects
------------

.. autoclass:: kyoukai.backends.httptools_.KyoukaiProtocol

.. autoclass:: kyoukai.backends.http2.H2KyoukaiComponent
	:members:

Asphalt
-------

These classes are for Asphalt usage, such as contexts.
You are not guaranteed to always have these specific objects.

.. autoclass:: kyoukai.asphalt.HTTPRequestContext
	:members:

.. autoclass:: kyoukai.asphalt.KyoukaiComponent
	:members:
