.. _gettingstarted:

Your First Kyoukai App
======================

In this tutorial, we'll go through how to write your first Kyoukai app.

Application Skeleton
--------------------

Strap in with your favourite IDE, and create your first new project.
Name it something silly, for example ``my-first-kyokai-project``. The
name doesn't matter, as you probably won't be using it for long.

Directory layout
~~~~~~~~~~~~~~~~

Kyoukai projects have a very simple layout.

::

    $ ls --tree

    ├── app.py
    ├── static
    └── templates

There are three components here:

-  ``app.py``

   -  This contains the main code for your app. This can be named
      absolutely anything, but we're naming it ``app`` for simplicity's
      sake.

-  ``templates``

   -  This contains all the templates used for rendering things
      server-side, or for putting your JS stack of doom inside.

-  ``static``

   -  This contains all the static files, such as your five bootstrap
      theme CSS files, or the millions of JS libraries you've included.

Writing the App
---------------

Open up ``app.py`` and add your starting line.

.. code-block:: python

    from kyoukai import Kyoukai

This imports the Kyoukai application class from the library, allowing you
to create a new object inside your code.

Creating the App Object
~~~~~~~~~~~~~~~~~~~~~~~

The central object in your file is the :class:`.Kyoukai` object. This object is core for handling
requests from clients, including routing and handling errors.

.. code-block:: python

    app = Kyoukai("my_app")

The name passed into the constructor is the **application name** - right now, this is irrelevant.
However, it is a required param, so you should pass something like your application's name.

Routes
~~~~~~

Routes in Kyoukai are very simple, and if you have ever used Flask, are
similar in style to Flask routes.

Routes are made up of three parts:

-  The path

   -  This is a Werkzeug-based route path that uses Werkzeug to match route paths.
      For more information, see http://werkzeug.pocoo.org/docs/0.11/routing/ .

-  The allowed methods

   -  This is a list, or set, or other iterable, of allowed HTTP/1.1
      methods for the route to handle. If a method (e .g ``GET``) is not
      in the list, the route cannot handle it, and a HTTP 405 error will
      automatically be passed to the client.

-  The route itself

   -  Your route is a coroutine that accepts one argument, by default:
      the a new :class:`~.HTTPRequestContext`, containing the request data
      and other context specific data.

   .. code-block:: python

       async def some_route(ctx: HTTPRequestContext): ...

We are going to write a very simple route that returns a
``Hello, world!`` file.

Creating the route
------------------

Routes in Kyoukai are created very similarly to Flask routes: with a
decorator.

.. code-block:: python

    @app.route("/path", methods=["GET", "POST"])

.. note::

    As explained above, the route decorator takes a path and a method.
    This route decorator returns a Route class, but this isn't important right now.

The router decorator can be found on one of two objects:

    - Your :class:`.Kyoukai` application object (which internally reroutes it to
        :attr:`.Kyoukai.root`)

    - A :class:`.Blueprint` application object.

The Route Coroutine
~~~~~~~~~~~~~~~~~~~

Your route function **must** be a coroutine. As Kyoukai is async,
your code must also be async.

.. code-block:: python

    @app.route("/")
    async def index(ctx): ...


Inside our route, we are going to return a string containing the
rendered text from our template.

Templates
~~~~~~~~~

Templates are stored in ``templates/``, obviously. They are partial HTML
code, which can have parts in it replaced using code inside the template
itself, or your view.

For now, we will put normal HTML in our file.

Open up ``templates/index.html`` and add the following code to it:

.. code-block:: html

    It's current year, and you're still using blocking code? Not <em>me!</em>

.. warning::
    Do not replace current year with the actual current year.

Save and close the template.

Rendering the template
~~~~~~~~~~~~~~~~~~~~~~

Since the template is a very simple HTML document, no additional rendering is needed; you can
simply use :func:`.as_html` to render the document.

.. code-block:: python

    @app.route("/")
    async def index(ctx):
        with open("templates/index.html") as f:
            return as_html(f.read())


:func:`.as_html` requires an extra import, ``from kyoukai.util import as_html`` to use. For more
information about these helper functions, see :ref:`req_response`.

Responses
---------

Note, how in the previous coroutine, we simply returned a ``str`` in our
route. This is not similar to ``aiohttp`` and the likes who force you to
return a ``Response``. You can return a response object in Kyoukai as
normal, but for convenience sake, you can also return simply a string or
a tuple.

These are transparently converted behind the scenes:

.. code-block:: python

    r = Response(code=route_result[1] or 200, body=route_result[0], headers=route_result[2] or {})

That is, the first item is converted to your response body, the second
item (or 200 by default) is used as the response code, and the third
code is used as the headers.

.. note::

   All return params except the first is optional, if you do not return a
   Response object.

Running your App
----------------

The ideal way of running a Kyoukai project is through the Asphalt
framework. See :ref:`asphalt usage` for more
information on how to use this.

However, Kyoukai includes a built-in way of running the app from
blocking code.

.. code-block:: python

    app.run(ip="127.0.0.1", port=4444)

.. note::

    The args passed in here are just the default values; they are optional.

Open up your web browser and point it to http://localhost:4444/. If you have done this correctly,
 you should see something like this:

.. figure:: /img/ex1.png
   :alt: example 1

   example 1

Deploying
---------

There's no special procedure for deploying your app. The inbuilt webserver is production ready,
and you can run your application in a production environment in the same way as you would develop
it.


Finishing your project
----------------------

You have completed your first Kyoukai project. For maximum effectiveness,
you must now publish it to GitHub.

.. code-block:: bash

    $ git init
    $ git remote add origin git@github.com:YourName/my-first-kyoukai-project.git
    $ git add .
    $ git commit -a -m "Initial commit, look how cool I am!"
    $ git push -u origin master
