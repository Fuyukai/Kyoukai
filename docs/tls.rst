.. _tls:

.. versionadded:: 2.1

HTTPS Support
=============

Kyoukai's built in web server comes with native TLS support with secure defaults. Enabling it is as simple as
creating a new block in the config file:

.. code-block:: yaml

    # The SSL configuration for the built-in webserver
    ssl:
        # Is SSL enabled?
        # If this is False, the certfile and keyfile will not be loaded.
        enabled: true

        # The public key certificate for the webserver to use.
        ssl_certfile: server.crt

        # The private keyfile for the webserver to use.
        ssl_keyfile: server.key

HTTPS will then automatically be enabled for this connection.

HTTP and HTTPS multiplexing
===========================

This is **not** currently supported.
