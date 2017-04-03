.. _routegroups:

Route Groups
============

.. versionadded:: 2.1.2

**Route Groups** are a way of grouping routes together into a single class, where they can all
access the members of the class. This is easier than having global shared state, and easily
allows having "route" templates.

Creating a Route Group
----------------------

All route groups descend from :class:`.RouteGroup`, or use :class:`.RouteGroupType` as the
metaclass. The former uses the latter as its metaclass, which is a shorter version.

.. code-block:: python

    from kyoukai.routegroup import RouteGroup, RouteGroupType

    # form 1, easiest form
    class MyRouteGroup(RouteGroup):
        ...

    # form 2, explicit metaclass
    class MyRouteGroup(metaclass=RouteGroupType):
        ...

.. note::

    By default, route groups have no magic ``__init__``. You are free to implement this in
    whatever way you like, including passing parameters to it.


Adding Routes
-------------

To make your route group useful, you need to add some **routes** to it. The RouteGroup module
includes a special decorator that marks a route function as a new :class:`.Route` during instance
creation, :meth:`~.routegroup.route`.

This method takes the same arguments as the regular ``route`` decorator; the only difference is
that it returns the original function in the class body rather than returning a new Route object.
Instead, certain attributes are set on the new function that are picked up during scanning,
such as ``in_group``.

.. code-block:: python

    from kyoukai.routegroup import RouteGroup, route

    class MyRouteGroup(RouteGroup):
        @route("/heck", methods=("GET", "POST"))
        async def heck_em_up(self, ctx: HTTPRequestContext):
            return "get hecked"

This will register ``heck_em_up`` as a route on the new route group.

.. autofunction:: kyoukai.routegroup.route
    :noindex:

Error Handlers
--------------

.. versionadded:: 2.1.3

Route groups can also have group-specific error handlers, using :func:`~.routegroup.errorhandler`.

.. code-block:: python

    @errorhandler(500)
    async def handle_errors(self, ctx, exc):
        ...

.. autofunction:: kyoukai.routegroup.errorhandler
    :noindex:

Request Hooks
-------------

.. versionadded:: 2.1.3

Route groups can have both Blueprint-specific error handlers, and route-specific error handlers,
using the helper functions.

For Blueprint-specific, you can use :func:`~.routegroup.hook` (or, better, aliases
:func:`~.routegroup.before_request` and :func:`~.routegroup.after_request`).

.. code-block:: python

    @before_request
    async def before_req(self, ctx):
        ...

Adding route-specific hooks is possible by calling ``@route.hook`` on the newly wrapped function.
This is achieved by setting a special decorator function on the function object modified by the
route decorator.

.. code-block:: python

    @heck_em_up.before_req
    async def whatever(self, ctx):
        ...

.. autofunction:: kyoukai.routegroup.hook
    :noindex:

.. autofunction:: kyoukai.routegroup.before_request
    :noindex:

.. autofunction:: kyoukai.routegroup.after_request
    :noindex:

.. py:decorator:: func.hook(type_: str)

    Marks a function as a route-specific hook.

    :param type_: The type of hook to add.

.. py:decorator:: func.before_request

    Marks a function as a before-request hook.

.. py:decorator:: func.after_request

    Marks a function as an after-request hook.


Registering the Group
---------------------

Adding the group to your app is as simple as instantiating the group and calling
:meth:`.Blueprint.add_route_group` with the instance.

.. code-block:: python

    rg = MyRouteGroup()
    app.root.add_route_group(rg)

Of course, an alias for this exists on :class:`~.app.Kyoukai` which redirects to the root blueprint.

.. automethod:: kyoukai.blueprint.Blueprint.add_route_group
    :noindex:

Customizing the Blueprint
-------------------------

Route groups work by using an underlying Blueprint that is populated with all the routes from the
class body during instantiation. The Blueprint can be customized by passing arguments in the
class definition to the metaclass, which are stored and later used to create the new Blueprint
object.

.. code-block:: python

    class MyRouteGroup(RouteGroup, prefix="/api/v1")
        ...

To get the blueprint object from a RouteGroup instance, you can use :meth:`~.get_rg_bp`.

.. autofunction:: kyoukai.routegroup.get_rg_bp
    :noindex:
