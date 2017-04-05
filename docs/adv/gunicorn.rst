.. _gunicorn:

Running Under gunicorn
======================

The inbuilt HTTP server works "well enough" for nearly all purposes that can be thought of,
including automatic HTTP/2 negotiation. However, you may wish to use a different WSGI server,
such as gunicorn. Kyoukai comes with an adaptor that can be used for this purpose.


The Adapter
-----------

The adapter is a replacement for the normal HTTP server, and as such will take over the HTTP
parsing from the httptools backend, using `aiohttp <https://aiohttp.readthedocs.org/en/stable/>`_,
via the ``gaiohttp`` worker.

Creating the adaptor is incredibly simple:

.. code-block:: python

    from kyoukai.backends.gunicorn import GunicornAdapter

    # make sure to have an app object already provided
    adapter = GunicornAdapter(my_app_object)

    # expose the ``run_application`` method for gunicorn to run
    application = adapter.run_application

Running gunicorn requires usage of the right worker, which is the ``gaiohttp`` worker:

.. code-block:: bash

    $ gunicorn -k gaiohttp my_app:application

Your Kyoukai app will now be running under gunicorn.


Asphalt Configuration
---------------------

It is also possible to run your Asphalt configuration via gunicorn with the usage of
:func:`.GunicornAdapter.from_asphalt_config`:

.. code-block:: python

    # make sure ``run_server`` is False in your config file!
    adapter = GunicornAdapter.from_asphalt_config("config.yml")
    application = adapter.run_application
