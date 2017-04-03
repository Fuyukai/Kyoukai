.. _http2:

HTTP/2 Support
==============

.. versionadded:: 2.1.0

Kyoukai comes with built in support for HTTP/2, thanks to to the H2 library.

Enabling HTTP2 requires:

 - TLS/SSL to be enabled

 - ``h2`` to be installed

 - The ``http2`` key in the config to be True, or manual switching to be enabled

Automatic switching
-------------------

Kyoukai supports automatically upgrading to HTTP/2 via ALPN/NPN protocols (the default for making
new connections over TLS) or with plain old h2c.

To enable **automatic upgrade**, add the ``http2`` key to your config file, under the ``kyoukai``
component, like so:

.. code-block:: yaml

    # Enables automatic HTTP/2 connection switching.
    # This will switch to the HTTP/2 protocol parser when a connection is created.
    http2: true

Now, when connecting over TLS (or HTTP/1.1 with h2c) the connection will be automatically
upgraded to a HTTP/2 connection.

Manual switching
----------------

It is possible to enforce HTTP/2 only, or otherwise manual switching, with the usage of
:class:`~.H2KyoukaiProtocol`.

To switch to this component, change ``KyoukaiComponent`` to ``H2KyoukaiComponent`` in your
application component
container like so:

.. code-block:: python

        self.add_component('kyoukai', H2KyoukaiComponent, ip="127.0.0.1", port=4444,
                        app=app)

API Ref
-------

.. autoclass:: kyoukai.backends.http2.H2KyoukaiComponent
    :members:
    :noindex:

.. autoclass:: kyoukai.backends.http2.H2KyoukaiProtocol
    :members:
    :noindex:

.. autoclass:: kyoukai.backends.http2.H2State
    :members:
    :noindex:
