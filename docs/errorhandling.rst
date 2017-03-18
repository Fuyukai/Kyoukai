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
    async def handle_500(ctx: HTTPRequestContext, exc: HTTPException):
        return repr(exception_to_handle)

Of course, you can have anything in the body of the error handler. Whatever is returned from this error handler is
sent back to the client.

.. warning::

    Due to how Kyoukai handles parameter checking, you **must** have your exception parameter named as ``exc``.
    Failure to do this will mean the exception is not passed properly.

HTTP Exceptions
---------------

HTTP exceptions in Kyoukai are handled by Werkzeug, which prevents having to rewrite large amounts of the error
handling internally.

For more information on Werkzeug's HTTPException, see :class:`werkzeug.exceptions.HTTPException`.

To abort out of a function early, you can use :meth:`werkzeug.exceptions.abort` to raise a HTTPException:

.. code-block:: python

    if something is bad:
        abort(404)
