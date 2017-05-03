.. _req_response:

Requests and Responses
======================

Requests and Responses are crucial parts of a HTTP framework - the request contains data that is
received from the client, and the Response contains data that is sent to the Client.

Kyoukai piggybacks off of Werkzeug for its request and response wrappers - this means that most of
the form logic and etc is handled by a well tested library used in thousands of applications
across the web.

Getting the Request
-------------------

The :class:`~werkzeug.wrappers.Request` object for the current request is available on
:attr:`~.HTTPRequestContext.request` for your route functions to use.

For example, returning a JSON blob of the headers:

.. code-block:: python

    async def my_route(ctx: HTTPRequestContext):
        headers = json.dumps(dict(ctx.request.headers))
        return headers

Creating a Response
-------------------

Responses are **automatically** created for you when you return from a route function or error
handler. However, it is possible to create them manually:

.. code-block:: python

    async def my_route(ctx: HTTPRequestContext):
        return Response("Hello, world", status=200)


Response Helpers
----------------

.. versionadded:: 2.1.3

There are some built-in helper functions to encode data in a certain form:

.. autofunction:: kyoukai.util.as_html
    :noindex:

.. autofunction:: kyoukai.util.as_plaintext
    :noindex:

.. autofunction:: kyoukai.util.as_json
    :noindex:
