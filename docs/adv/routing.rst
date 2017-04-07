.. _adv_routing:

Advanced Routing
================

Kyoukai supports some advanced features of Werkzeug's routing, such as building URLs from an
endpoint automatically.

Subdomain Support
-----------------

This is a TODO, and will be implemented in a later version.

URL Building
------------

URL building from endpoints is supported via the usage of either
:meth:`.HTTPRequestContext.url_for` or :meth:`.Blueprint.url_for`. The former is recommended over
the latter as it automatically provides the environment for the Map to bind to.

Endpoints
~~~~~~~~~

Endpoints for the usage in URL building are generated using a simple formula::

    - take the name of the Blueprint

    - take the name of the callable for the route

    - combine them separated by a single dot (.)

For example, a Blueprint defined as ``Blueprint("api")`` and a route defined as
``def get_all_users(...)`` will have the endpoint of ``api.get_all_users``. It is possible to
override the endpoint by passing ``endpoint=`` to either :func:`.Blueprint.wrap_route` or
:func:`.Blueprint.route` (and the route group equivalent).

.. versionchanged:: 2.2.0

    Added the ability to override the endpoint for a route.


Building the URL is simple:

.. code-block:: python

    url = ctx.url_for("api.get_all_users")

If the same endpoint has multiple methods, pass ``methods`` to the function:

.. code-block:: python

    url = ctx.url_for("api.something_with_users", methods=["POST"])

To enforce *external URLs only* (i.e not relative), pass ``force_external = True``:

.. code-block:: python

    url = ctx.url_for("api.get_all_users", force_external=True)

Finally, if your route is defined with parameters (e.g ``def get_user(ctx, user_id: int)``):

.. code-block:: python

    url = ctx.url_for("api.get_all_users", user_id=1)

Multiple Paths For One Route
----------------------------

This is a TODO, and will be implemented in a later version.

