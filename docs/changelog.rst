Kyoukai Changelog
=================

Here you can see the list of changes between each Kyoukai release.

Version 2.1.3
-------------

  - Add :meth:`~.routegroup.errorhandler` to mark a function inside a route group as an error
    handler.

Version 2.1.2
-------------

  - Add :class:`.RouteGroup`.

Version 2.1.1
-------------

  - Fix request bodies not being read properly.

  - Fix loop propagation.

  - Fix http2 module for H2 3.0.0.

Version 2.1.0
-------------

  - Add :attr:`.Route.hooks` property to :class:`~.Route`, which allows route-specific hooks.

  - Add the ability to disable argument conversion on :class:`~.Route` objects.

  - Automatically disable argument conversion on error handlers.

  - HTTP/2 is now automatically enabled in all requests over TLS, if available.

  - HTTPS is now easier to configure (requires one config file change).

Version 2.0.5
-------------

  - Add ``REMOTE_ADDR`` and ``REMOTE_PORT`` to WSGI environ in httptools backend.

  - Add ``REMOTE_ADDR`` and ``REMOTE_PORT`` to WSGI environ in h2 backend.


Version 2.0.4.1
---------------

  - Automatically stringify the response body.

Version 2.0.3
-------------

  - Fix Content-Type and Content-Length header parsing.

  - Add automatic JSON form parsing.

  - Log when a HTTPException is raised inside a route function.

Version 2.0.2
-------------

  - Automatic argument conversion now ignores functions with _empty params.

Version 2.0.1
-------------

  - Error handlers can now handle errors that happen in other error handlers.

Version 2.0
-----------

Version 2.0 is a major overhaul of the library, simplifying it massively and removing a lot of redundant or otherwise overly complex code.

  - Requests and responses are now based on Werkzeug data structures.
    Werkzeug is a much more battle tested library than Kyoukai; it ensures that there are less edge cases during HTTP parsing.

  - Routing is now handled by Werkzeug and the Rule/Map based router rather than overly complex regex routes.

  - The application object is now I/O blind - it will take in a Request object and produce a Response object, instead of writing to the stream directly.

  - A new ``gunicorn`` HTTP backend has been added - using the ``gaiohttp`` worker, gunicorn can now be connected to Kyoukai.

  - A new ``uwsgi`` HTTP backend has been added - uWSGI running in asyncio mode can now be connected to Kyoukai.

  - A new HTTP/2 backend has been added which uses the pure Python ``h2`` library as a state machine for parsing HTTP frames.

  - The ``httptools`` backend has been rewritten - it is now more reliable and supports chunked data streams.

Version 1.9.2
-------------

 - Add ``depth`` property which signifies how deep in the tree the Blueprint is.

 - The routing tree no longer considers matching routes that don't start with the prefix of the blueprint.

 - Add ``tree_path`` property which shows the full tree path to a Blueprint.

 - Add the ability to set 405 error handlers on Blueprints.
   The routing engine will automatically try and match the 405 on the lowest common ancestor of all routes that
   failed to match in the blueprint tree.

 - Add ``blueprint`` and ``route`` attributes to :class:`~.HTTPRequestContext`.

 - Add ``ip`` and ``port`` attributes to :class:`~.Request`.

 - Correctly load cookies from the ``Cookie`` header from client requests.

 - Converters will now handle ``*args`` and ``**kwargs`` in functions properly.

 - HTTPExceptions have been overhauled to allow early exiting with a custom response. Do not abuse as a replacement
   for the return statement.

Version 1.9.1
-------------

 - Large amount of code clean up relating to the embedded HTTP server.
   The HTTP server now uses httptools to create requests which is more reliable than http_parser.

Version 1.8.6
-------------

 - Add a default static file handler.

Version 1.8.5
-------------

 - Routing tree has been improved by allowing two routes with the same path but different methods to reside in two
   different blueprints.

Version 1.8.4
-------------

 - Error handlers can now error themselves, and this is handled gracefully.

 - If a match is invalid, it will raise a 500 error at compile time, which is usually when routes are first matched.

Version 1.8.3
-------------

 - Converters can now be awaitables.

Version 1.8.2
-------------

 - JSON forms are now lazy loaded when ``.form`` is called.

Version 1.8.1
-------------

 - Fix crashing at startup without a startup function registered.

 - Fix routing tree not working with multiple URL prefixes.

 - Fix default converters.

Version 1.8.0
-------------

 - Add the ability to override the Request and Response classes used in views with ``app.request_cls`` and
   ``app.response_cls`` respectively.

 - Views now have the ability to change which Route class they use in the decorator.

 - Implement the Werkzeug Debugger on 500 errors if the app is in debug mode.

Version 1.7.3
-------------

 - Add the ability to register a callable to run on startup.
   This callable can be a regular function or a coroutine.

Version 1.7.2
-------------

 - Form handling is now handled by Werkzeug.

 - Add a new attribute, :attr:`kyoukai.request.Request.files` which stores uploaded files from the form passed in.

 - Requests are no longer parsed multiple times.

Version 1.7.0
-------------

 - Overhaul template renderers. This allows easier creation of a template renderer with a specific engine without
   having to use engine-specific code in views.

 - Add a Jinja2 based renderer. This can be enabled by passing ``template_renderer="jinja2"`` in your application
   constructor.

Version 1.6.0
-------------

 - Add converters.
   Converters allow annotations to be added to parameters which will automatically convert the argument passed in to
   that type, if possible.

 - Exception handlers now take an ``exception`` param as the second arg, whcih is the HTTPException that caused this
   error handler to happen.

Version 1.5.0
-------------

 - Large amount of internal codebase re-written.

 - The Blueprint system was overhauled into a tree system which handles routes much better than before.
