.. _hooks:

Request Hooks
=============

Request hooks are a convenient way of performing actions before and after a request is processed by your code. There
are several types of request hooks:

 - **Global-level** request hooks, which take action on ALL routes.
   These can be technically seen as **root blueprint-level** hooks, since they act on the root blueprint.

 - **Blueprint-level** request hooks, which take action at the blueprint level.
   These are registered on a blueprint, and act on **all routes** registered to that blueprint, *as well as* all
   routes registered to children blueprints.

 - **Route-level** request hooks, which take action on individual routes.

**All hooks must complete successfully.** If any hook fails, then the request will fail with a 500 Internal Server
Error.

.. note::

    Global-level hooks are registered with ``app.add_hook`` and family, but actually redirect to the root blueprint.

Adding a Hook
-------------

Adding a hook can be done with :meth:`~.Blueprint.add_hook` or :meth:`~.Route.add_hook`. These take a type param and
a the hook function to add.

Alternatively, you can use the helper functions:

.. automethod:: kyoukai.blueprint.Blueprint.before_request
    :noindex:
.. automethod:: kyoukai.route.Route.before_request
    :noindex:

.. automethod:: kyoukai.blueprint.Blueprint.after_request
    :noindex:
.. automethod:: kyoukai.route.Route.after_request
    :noindex:

Pre-request hooks
-----------------

**Pre-request** hooks are hooks that are fired before a request handler is invoked. They are fired in the order they
are added.

Pre-request hooks take one param: the :class:`HTTPRequestContext` that the request is going to be invoked with. They
can either return the modified context, a new context, or None to use the previous context as the new one.

.. code-block:: python

    async def print_request(ctx: HTTPRequestContext):
        print("Request for", ctx.request.path)
        return ctx  # can be omitted to leave `ctx` in place


Post-request hooks
------------------
**Post-request** hooks are hooks that are fired after a request is invoked. They are fired in the order they are added.

Post-request hooks take two params: The :class:`HTTPRequestContext` that the request was invoked with, and the
**wrapped result** (**NOT** the final result!) of the response handler. They can either return a modified Response,
or None to use the previous Response as the new one.

.. code-block:: python

    async def jsonify(ctx, response):
        if not isinstance(response.response, dict):
            return response

        r.set_data(json.dumps(response.response))
        return r

