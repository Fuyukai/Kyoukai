.. _req_response:

Requests and Responses
======================

Requests and Responses are crucial parts of a HTTP framework - the request contains data that is
received from the client, and the Response contains data that is sent to the Client.

Kyoukai piggybacks off of Werkzeug for its request and response wrappers - this means that most of
the request is handled by a well tested library used in thousands of applications across the web.

Getting the Request
-------------------

The :class:`~werkzeug.wrappers.Request` object for the current request is available on
:attr:`~.HTTPRequestContext.request` for your route functions to use.

For example, returning a JSON blob of the headers:

.. code-block:: python3

    async def my_route(ctx: HTTPRequestContext):
        headers = json.dumps(dict(ctx.request.headers))
        return headers


.. class:: werkzeug.wrappers.Request
    :noindex:

    Represents a request incoming from the client.

    .. autoattribute:: accept_charsets
    .. autoattribute:: accept_encodings
    .. autoattribute:: accept_languages
    .. autoattribute:: accept_mimetypes
    .. autoattribute:: accept_ranges
    .. autoattribute:: access_route
    .. autoattribute:: args
    .. autoattribute:: authorization
    .. autoattribute:: base_url
    .. autoattribute:: cache_control
    .. autoattirubte:: content_range
    .. autoattribute:: cookies
    .. autoattribute:: data
    .. autoattribute:: files
    .. autoattribute:: form
    .. autoattribute:: full_path
    .. autoattribute:: headers
    .. autoattribute:: host
    .. autoattribute:: host_url
    .. autoattribute:: if_match
    .. autoattribute:: if_modified_since
    .. autoattribute:: if_none_match
    .. autoattribute:: if_range
    .. autoattribute:: if_unmodified_since
    .. autoattribute:: is_secure
    .. autoattribute:: is_xhr
    .. autoattribute:: method
    .. autoattribute:: path
    .. autoattribute:: query_string
    .. autoattribute:: range
    .. autoattribute:: remote_addr
    .. autoattribute:: remote_user
    .. autoattribute:: scheme
    .. autoattribute:: trusted_hosts
    .. autoattribute:: url
    .. autoattribute:: url_charset
    .. autoattribute:: values

    .. automethod:: get_etag
    .. automethod:: get_data


Creating a Response
-------------------

Responses are **automatically** created for you when you return from a route function or error
handler. However, it is possible to create them manually:

.. code-block:: python3

    async def my_route(ctx: HTTPRequestContext):
        return Response("Hello, world", status=200)


.. class:: werkzeug.wrappers.Response
    :noindex:

    Represents a response from the server to the client.

    .. automethod:: __init__

    .. autoattribute:: data
    .. autoattribute:: headers
    .. autoattribute:: response
    .. autoattribute:: status
    .. autoattribute:: status_code

    .. automethod:: freeze
    .. automethod:: get_data
    .. automethod:: set_cookie
    .. automethod:: delete_cookie
    .. automethod:: set_data

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
