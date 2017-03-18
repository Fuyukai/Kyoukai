.. _blueprints:

.. versionadded:: 1.5

Blueprints
==========

In Kyoukai, routes are stored inside a tree structure consisting of multiple Blueprint objects with a parent and
children. Each Blueprint contains a group of routes stored on it, which inherit the request hooks and the API prefix
of all of its parents.

Blueprints are instantiated similar to app objects, with a name.

.. code:: python

    my_blueprint = Blueprint("my_blueprint")


Additionally, blueprints take an additional set of parameters which can be used to more finely control the behaviour.

   - ``url_prefix``: The URL prefix to add to every request.
        For example, if this is set to ``/api/v1`, every request attached to this blueprint will only be accessible
        via ``/api/v1/<route>``.

A note on the tree
------------------

Blueprints are stored inside a tree structure - that means that all Blueprints have a parent blueprint and 0 to N
children blueprints.

When registering an error handler, or a request hook, children blueprints automatically inherit these unless they are
 overriden on the child level.

Routing
-------

Routing with Blueprints is incredibly similar to routing with a bare app object. Internally, an ``@app.route`` maps
to routing on an underlying Blueprint object used as the "root" blueprint.

.. code:: python

    @my_blueprint.route("/some/route")
    async def some_route(ctx: HTTPRequestContext):
        return "Some route"

.. automethod:: kyoukai.blueprint.Blueprint.route
    :noindex:

Error handlers
--------------

Error handlers with Blueprints are handled exactly the same as error handlers on bare app objects. The difference
between these however is that error handlers are local to the Blueprint and its children.

.. code:: python

    @my_blueprint.errorhandler(500)
    async def e500(ctx: HTTPRequestContext, err: Exception):
        return "Handled an error"

.. automethod:: kyoukai.blueprint.Blueprint.errorhandler
    :noindex:


Registering blueprints
----------------------

If, after creating your blueprint, you attempt to navigate to ``/some/route`` you will find a 404 error living there
instead. This is because you did not register the Blueprint to your application.

.. code:: python

    app.register_blueprint(my_blueprint)

Internally, this adds a child to the root blueprint, and sets the parent of the child to the root blueprint.
If you have a blueprint that you wish to inherit from, you must register your Blueprint as a child of the Blueprint
you wish to inherit from.

.. code:: python

    my_blueprint.add_child(my_other_blueprint)

.. automethod:: kyoukai.app.Kyoukai.register_blueprint
    :noindex:

.. automethod:: kyoukai.blueprint.Blueprint.add_child
    :noindex:





