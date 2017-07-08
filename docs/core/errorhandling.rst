.. _errorhandling:

Handling Errors Within Your Application
=======================================

As with all code, eventually bugs and other exceptions will come up and risk ruining everything
inside your app.
Fortunately, Kyoukai handles these errors for you, and allows you to process them safely.

**Error handlers** are a way of handling errors easily. They are automatically called when an
exception is encounted inside a route.

For example, if you have a piece of faulty code:

.. code-block:: python

    return "{}".format(a)  # 'a' is not defined

A :class:`NameError` will normally be raised. However, Kyoukai will automatically catch the error,
and re-raise it as a HTTP 500 exception. Normally, this exception wouldn't be handled, and would
respond to the client with a ``500`` body. However, it is possible to catch this exception and do
what you wish with it.

The ``errorhandler`` decorator
------------------------------

To create an error handler, you simply wrap an existing function with the ``errorhandler``
decorator, providing the integer error code that you wish to handle. So for example, to create a
500 error handler, you would do:

.. code-block:: python

    @app.root.errorhandler(500)
    async def handle_500(ctx: HTTPRequestContext, exc: HTTPException):
        return repr(exception_to_handle)

Of course, you can have anything in the body of the error handler. Whatever is returned from
this error handler is sent back to the client.

.. versionadded:: 2.2.1

You can also have an error handler handle multiple codes in the same function by decorating it
multiple times, or passing a range of errors to handle.

.. code-block:: python

    # handle error 502 and errors 400 (inclusive) to 414 (exclusive)
    @app.root.errorhandler(500)
    @app.root.errorhandler(400, 414)
    async def handle_many(ctx: HTTPRequestContext, exc: HTTPException):
        ...

.. versionchanged:: 2.2.1

If you need to access the arguments provided in the route when handling an error, you can use
:attr:`.HTTPRequestContext.params`, which will be a dict of the parameters passed to the function
based on the routing URL.

HTTP Exceptions
---------------

HTTP exceptions in Kyoukai are handled by Werkzeug, which prevents having to rewrite large amounts
of the error handling internally.

For more information on Werkzeug's HTTPException, see :class:`werkzeug.exceptions.HTTPException`.

To abort out of a function early, you can use :meth:`werkzeug.exceptions.abort` to raise a
HTTPException:

.. code-block:: python

    if something is bad:
        abort(404)
