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

