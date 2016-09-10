.. _errorhandling:

Handling Errors Within Your Application
=======================================

As with all code, eventually bugs and other exceptions will come up and risk ruining everything inside your app.
Fortunately, Kyoukai handles these errors for you, and allows you to process them safely.

**Error handlers** are a way of handling errors easily. They are automatically called when an exception is encounted
inside a route.

For example, if you have a piece of faulty code:

.. code:: python

    return "{}".format(a)  # 'a' is not defined

A :class:`NameError` will normally be raised. However, Kyoukai will automatically catch the error, and re-raise it as
a HTTP 500 exception. Normally, this exception wouldn't be handled, and would respond to the client with a ``500``
body. However, it is possible to catch this exception and do what you wish with it.

The ``errorhandler`` decorator
------------------------------

To create an error handler, you simply wrap an existing function with the ``errorhandler`` decorator, providing the
integer error code that you wish to handle. So for example, to create a 500 error handler, you would do:

.. code:: python

    @app.root.errorhandler(500)
    async def handle_500(ctx: HTTPRequestContext, exception_to_handle: Exception):
        return repr(exception_to_handle)

Of course, you can have anything in the body of the error handler. Whatever is returned from this error handler is
sent back to the client.

HTTP Exceptions
---------------

HTTP Exceptions are a special type of exception, that don't represent an error but instead a way of instantly
dropping out of your route and into an error handler for the appropriate code.

They're very easy to raise - you have two options:

1) Use the :meth:`kyoukai.exc.HTTPException.new` classmethod to create a new HTTPException.

.. automethod:: kyoukai.exc.HTTPException.new


2) Use :meth:`kyoukai.exc.abort` to handle raising the exception.

.. automethod:: kyoukai.exc.abort
    :noindex:
