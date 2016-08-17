Kyoukai Changelog
=================

Here you can see the list of changes between each Kyoukai release.

Version 1.8.0
-------------

 - Add the ability to override the Request and Response classes used in views with ``app.request_cls`` and
   ``app._response_cls`` respectively.

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
