.. _asphalt usage:

Asphalt usage
=============

The **Asphalt Framework** is a microframework for asyncio-based applications and libraries, providing useful
utilities and common functions to projects built upon it.

It also provides a common interface for applications to use *components* to enhance the functionality in an easy
asynchronous way.


Config File
-----------

The core part about adding Asphalt to your project is the ``config.yml`` file that exists at the core of every app.
This defines how the application should be ran, and what settings each component within should have.

These config files are standard YAML files, with one document. An example file for a Kyoukai project would be:

.. code:: yaml

    ---
    component:
      type: kyoukai.asphalt:KyoukaiComponent
      app: app:kyk


Let's break this down.

    1. First, you have the ``component:`` directive. This signifies to Asphalt that you wish to define a list of
    components to add to your project.

    2. Next, you have the ``type`` directive. This tells Asphalt what type of component to use in the application.

    In this example, the :class:`KyoukaiComponent` is specified directly, meaning that you wish the framework to
    create a single-component application, with the root component being Kyoukai's handler.

    3. Finally, the ``app`` directive. This tells the :class:`KyoukaiComponent` to use the app specified by the
    string here.

    In ``app:kyk``, the first part before the : signifies the FULL IMPORT NAME (the name you would use in an import
    statement, e.g ``import app``), and the second part signifies the object to use.

To run an app using Asphalt, you merely need to run:

.. code:: bash

    asphalt run config.yml

The Asphalt runner will automatically run and load your application.

Adding Components
-----------------

**Components** are a way of adding useful parts to your project without additional manual set up. In this example, we
 will add a SQLAlchemy component to the app.

The Container
~~~~~~~~~~~~~

First, a new **container** object is required to store the components that are added to the application. Every
container is inherited from :class:`asphalt.core.component.ContainerComponent` in order to add components to the app.

We're gonna start with a small project layout:

::

    $ ls --tree

    ├── application
    │	└── container.py
    ├── static
    └── templates

This will be the basic project format from now on.

Inside ``container.py``, add the following code:

.. code:: python

    from asphalt.core import ContainerComponent, Context
    from kyoukai import Kyoukai
    from kyoukai import KyoukaiComponent

    app = Kyoukai("api")


    class AppContainer(ContainerComponent):
         async def start(self, ctx: Context):
            self.add_component('kyoukai', KyoukaiComponent, ip="127.0.0.1", port=4444,
                                app=app)

            await super().start(ctx)

That's a lot of code to process. Let's break it down again.

 1. First, you have the creation of the app.  Nothing unusual here.

 2. Next, the definition of a subclass for the app.  This container contains a set of components, which are added to
 the app at run time, and configured appropriately.

 3. The addition of the KyoukaiComponent to the app. This adds the Kyoukai handler to Asphalt, which configures the
 application to run with additional contexts.

 4. A super call, which tells Asphalt to run our app immediately.

We're not done yet, however. Now, the config file needs to be run.

Add a basic configuration file, named ``config.yml``, with this simple piece of code.

.. code:: yaml

    ---
    component:
      type: application.container:AppContainer
      components:
        kyoukai:
          ip: "127.0.0.1"
          port: 4444

This creates a new AppContainer instance, and edits the configuration of the Kyoukai component within to set the IP
and port to the ones in the config file.

To run this application, it's as simple as the first Asphalt call:

::

    asphalt run config.yml


Adding SQLAlchemy
~~~~~~~~~~~~~~~~~

Now that you've seen how to add basic components to your project, adding SQLAlchemy is easy.

Edit your ``start`` method in your ``AppContainer`` to add this line above your super call:

.. code:: python

    self.add_component('sqlalchemy', SQLAlchemyComponent)

Make sure to the add the import for this (``from asphalt.sqlalchemy.component import SQLAlchemyComponent``) too.

Next, in your config.yml, add a new section under ``components``:

.. code:: yaml

   sqlalchemy:
      url: "sqlite3:///tmp/database.db"
      metadata: application.db:metadata

This will automatically configure a SQLite3 database at ``/tmp/database.db`` to run with your application.

Note that the reference for the metadata doesn't exist. You create your metadata like any other SQLAlchemy
application, however you don't add an engine or a session. The engine and session are automatically provided.

