"""
A Kyoukai app is the core container of a web application based upon the framework.
"""

import asyncio
import inspect
import io
import mimetypes
import os
import traceback
import logging
import typing

from kyoukai.renderers.base import Renderer
from kyoukai.views import View

try:
    import magic
except (ImportError, OSError):
    _has_magic = False
else:
    _has_magic = True
from asphalt.core import Context

from asphalt.core.runner import run_application
from typeguard import check_argument_types

from kyoukai.blueprints import Blueprint
from kyoukai.context import HTTPRequestContext
from kyoukai.util import static_filename, wrap_response

from kyoukai.exc import HTTPException
from kyoukai.response import Response
from kyoukai.route import Route

try:
    from kyoukai.renderers import mako_renderer

    _has_mako = True
except ImportError:
    mako_renderer = None
    _has_mako = False

try:
    from kyoukai.renderers import jinja_renderer

    _has_jinja2 = True
except ImportError:
    jinja_renderer = None
    _has_jinja2 = False


class Kyoukai(object):
    """
    A Kyoukai app.

    This is the core component to your web application based on Kyoukai.

    :param name:
        The name of the app. This is passed into the root blueprint as the name, which shows up in exceptions.
    :type name: :class:`str`
    """

    def __init__(self, name: str, **kwargs):
        """
        Create a new app.
        """

        self.name = name
        self.loop = asyncio.get_event_loop()

        self.logger = logging.getLogger("Kyoukai")

        self.error_handlers = {}

        # Define the config.
        self.config = kwargs

        # Define the "root" blueprint, which is used for @app.request.
        self._root_bp = Blueprint(name, None)

        self.debug = kwargs.get("debug", False)

        # Define the component here so it can be checked easily.
        self.component = None

        # On startup function.
        self._on_startup = lambda: None

        # Define the renderer.
        render = kwargs.get("renderer")
        if render == "mako":
            if not _has_mako:
                raise ImportError("Mako is not installed; cannot be used as a renderer")
            else:
                self._renderer = mako_renderer.MakoRenderer(kwargs.get("template_directory"))
        elif render == "jinja2":
            if not _has_jinja2:
                raise ImportError("Jinja2 is not installed; cannot be used as a renderer")
            else:
                self._renderer = jinja_renderer.Jinja2Renderer(kwargs.get("loader"))

    def reconfigure(self, **cfg: dict):
        """
        Reconfigures the app using the parameters passed in from the config.

        This is used, for example, with Asphalt's config and the KyoukaiComponent's consume rest behaviour when
        dealing with keyword arguments.

        :param cfg: A dictionary of config values to reconfigure the application with.
        :return: The new configuration.
        """
        self.config = {**self.config, **cfg}
        return self.config

    @property
    def renderer(self) -> Renderer:
        """
        :return: The current :class:`kyoukai.renderers.Renderer` configured for this application.
        """
        return self._renderer

    @property
    def root(self):
        """
        This property is a way to access the root blueprint.

        The root blueprint is the parent of all registered blueprints in the application. It can be used to directly
        route onto the top-level, however it is recommended to just use :meth:`Kyoukai.route` and similar to run onto
        the root blueprint.
        """

        return self._root_bp

    def register_blueprint(self, bp: Blueprint):
        """
        Registers a blueprint as a sub-blueprint to the root blueprint.

        :return: The modified Blueprint with the correct parent.
        """
        assert check_argument_types()
        self._root_bp.add_child(bp)
        if bp.parent is None:
            bp.parent = self._root_bp
        return bp

    def render(self, filename: str, **kwargs) -> str:
        """
        Render a template using the currently loaded rendering engine.

        :param filename: The filename of the template to load and render.
        :type filename: str

        :param kwargs: Additional arguments to pass to the template renderer.
                These are directly passed to :meth:`mako.template.Template.render` to render the template.

        :return: A :class:`str` containing the rendered information.
        """
        return self.renderer.render(filename, **kwargs)

    def render_template(self, filename: str, code=200, **kwargs) -> Response:
        """
        Render a template using the currently loaded rendering engine.

        Unlike :meth:`Kyoukai.render`, this returns a :class:`Response` object.

        :param filename: The filename of the template to load and render.
        :type filename: str

        :param code: The response code to add into the Response.

        :param kwargs: Additional arguments to pass to the template renderer.
                These are directly passed to :meth:`mako.template.Template.render` to render the template.

        :return: A :class:`Response` object with the rendered template.
        """
        data = self.render(filename, **kwargs)
        # Wrap it in a response.
        return Response(code, data, headers={"Content-Type": "text/html"})

    def get_static_path(self, filename: str) -> str:
        """
        Gets a sanitized static path.

        This will use the current working directory and the `static_dir` defined by the configuration, or `static` if
        that is not specified, to build the full path.

        :param filename: The filename to look up.
        :return: A :class:`str` with the fully built path.
        """
        return os.path.join(os.getcwd(), self.config.get("static_dir", "static"), static_filename(filename))

    def get_static_file(self, filename: str) -> io.BufferedIOBase:
        """
        Opens and returns a static file from the path.

        Internally, this uses :meth:`Kyoukai.get_static_path` to sanitize the path.

        :param filename: The filename to load.
        :return: A file object opened in binary mode, attached to the file.
        :rtype: :class:`io.BufferedIOBase`
        """
        fname = self.get_static_path(filename)
        if not os.path.exists(fname):
            return None
        else:
            return open(os.path.join(os.getcwd(), self.config.get("static_dir", "static"), fname), 'rb')

    def get_static(self, filename: str) -> Response:
        """
        Gets a file, using static, but returns a Response instead of the file handle.
        """
        content = self.get_static_file(filename)
        if not content:
            raise HTTPException(404)

        with content:
            path = self.get_static_path(filename)
            mimetype = mimetypes.guess_type(path)[0]
            if not mimetype:
                if _has_magic:
                    mimetype = magic.from_file(path, mime=True).decode()
                else:
                    mimetype = "application/octet-stream"
            return Response(200, body=content.read(), headers={"Content-Type": mimetype})

    def _match_route(self, path, meth) -> Route:
        """
        Match a route, based on the regular expression of the route.

        :return: The :class:`kyoukai.Route` of the route that matches, or None if no route matches.
        :raises: :class:`kyoukai.exc.HTTPException` if the route matches, but the method is not allowed.
        """
        return self._root_bp.match(path, meth)

    def route(self, regex, *, methods: list = None, run_hooks=True):
        """
        Convenience decorator to create a new route.

        This is equivalent to:

        .. code:: python

            route = bp.wrap_route(regex, callable, methods, run_hooks)
            bp.add_route(route)

        .. note::

            This function is a shortcut to ``app.root.route(*args, **kwargs)``.

        :param regex: The regular expression to match the path to. This uses standard Python :mod:`re` syntax.
                Group matches are automatically extracted from the regex, and passed as arguments.

        :param methods: The list of allowed methods, e.g ["GET", "POST"].
                You can check the method with `request.method`.

        :param run_hooks: Should the pre and post request hooks run automatically?
                This is set to True by default.
        """
        return self._root_bp.route(regex, methods=methods, run_hooks=run_hooks)

    def errorhandler(self, code: int):
        """
        Convenience decorator to add an error handler.

        This is equivalent to:

        .. code:: python

            route = bp.wrap_route("", coro, methods=[], run_hooks=False)
            bp.add_errorhandler(code, route)

        .. note::

            This function is a shortcut to ``app.root.errorhandler(code)``.
        """
        return self._root_bp.errorhandler(code)

    errorhandler.__doc__ = Blueprint.errorhandler.__doc__

    def log_request(self, ctx: HTTPRequestContext, code: int = 200):
        """
        Logs a request to the logger.

        This is an **internal** method and should not be used by user code.

        :param ctx: The :class:`kyoukai.context.HTTPRequestContext` to log from.
        :param code: The error code to log. Defaults to 200.
        """
        try:
            route = ctx.request.path
        except AttributeError:
            # *really* bad request - ignore it.
            return
        self.logger.info("HTTP/{} {} {} - {}".format(ctx.request.sversion, ctx.request.method, route, code))

    def before_request(self, func):
        """
        Set a coroutine to run as before the request.

        This coroutine should take in the HTTPRequestContext, and return a new HTTPRequestContext.

        .. note::

            This function is a shortcut to ``app.root.before_request(func)``.
        """
        return self._root_bp.before_request(func)

    def after_request(self, func):
        """
        Set a coroutine to run after the request.

        This coroutine should take in a :class:`Response`, and return a :class:`Response`.

        .. note::

            This function is a shortcut to ``app.root.after_request(func)``.
        """

        return self._root_bp.after_request(func)

    def bind_view(self, view: View):
        """
        Binds a view class to a Blueprint.

        This takes the *class*, not the instance, as a param.

        It also takes args and keyword args to instantiate the class with.

        .. note::

            This function is a shortcut to ``app.root.bind_view(view)``.
        """
        self._root_bp.bind_view(view)

    async def call_on_startup(self):
        """
        Calls the on_startup handler.

        This should not be called, unless you wish to call the startup function again (?).
        """
        item = self._on_startup()
        # If it's a coroutine or otherwise awaitable, await it.
        # This is so that coroutines can be passed in to handle.
        if inspect.isawaitable(item):
            await item

    def on_startup(self, coro_or_callable: typing.Callable[[], None]):
        """
        Registers a function to be called on startup.

        The function should be a callable.
        :return: The unmodified callable.
        """
        if not callable(coro_or_callable):
            raise TypeError("Object {} is not callable".format(coro_or_callable))
        self._on_startup = coro_or_callable

        return coro_or_callable

    async def handle_http_error(self, err: HTTPException, protocol, ctx: HTTPRequestContext):
        """
        Handle a :class:`kyoukai.exc.HTTPException`.

        This will invoke the appropriate error handler as registered in the blueprint of the route, if we can.
        Otherwise, it will invoke the default error handler.
        """
        code = err.code
        route = err.route
        # Check if the route is None.
        # If it is, we just have to use the default blueprint to handle the exception.
        if not route:
            bp = self._root_bp
        else:
            bp = route.bp

        # Get the error handler.
        error_handler = bp.get_errorhandler(code)
        if not error_handler:
            # Since there's no special error handler derived for this code, return a basic Response.
            # If it's a 500 and we're in debug mode, format the traceback.
            if err.code == 500 and self.debug:
                body = traceback.format_exc()
            else:
                body = str(code)
            resp = Response(code, body, {"Content-Type": "text/plain"})
        else:
            # Invoke the error handler specified.
            resp = wrap_response(await error_handler.invoke(ctx, exception=err))
        protocol.handle_resp(resp)

        # Check if we should close the connection.
        if hasattr(ctx.request, "should_keep_alive"):
            if not ctx.request.should_keep_alive:
                protocol.close()
        else:
            # If it's that bad, just close it anyway.
            protocol.close()

        return resp

    async def delegate_request(self, protocol, ctx: HTTPRequestContext):
        """
        Handles a :class:`kyoukai.context.HTTPRequestContext` and it's underlying request, processing it to the route
        handlers and such in the blueprints.

        This is an **internal** method, and should not be used outside of the protocol, or for testing.
        """
        async with ctx:
            # Acquire the lock on the protocol.
            async with protocol.lock:
                # Check if there's a host header.
                if ctx.request.version == (1, 1):
                    host = ctx.request.headers.get("host", None)
                    if not host:
                        exc = HTTPException(400)
                        self.log_request(ctx, code=400)
                        await self.handle_http_error(exc, protocol, ctx)
                        return
                # First, try and match the route.
                try:
                    route = self._match_route(ctx.request.path, ctx.request.method)
                except HTTPException as e:
                    # We matched it; but the route doesn't work for this method.
                    # So we catch the 405 error,
                    if e.code == 405:
                        self.log_request(ctx, code=e.code)
                        await self.handle_http_error(e, protocol, ctx)
                        return
                    else:
                        self.logger.error("??????? Something went terribly wrong.")
                        return

                # If the route did not match, return a 404.
                if not route:
                    fof = HTTPException(404)
                    self.log_request(ctx, code=404)
                    await self.handle_http_error(fof, protocol, ctx)
                    return

                # Try and invoke the Route.
                try:
                    # Note that this will already be a Response.
                    # The route should call `app._wrap_response` when handling the response.
                    # This is because routes are responsible for pre-route and post-route hooks, calling them in the
                    # blueprint as appropriate.
                    # So we just pass ourselves to the route and hope it invokes properly.
                    response = await route.invoke(ctx)
                except HTTPException as e:
                    # Handle a HTTPException normally.
                    self.log_request(ctx, e.code)
                    # Set the route of the exception.
                    e.route = route
                    await self.handle_http_error(e, protocol, ctx)
                    return
                except Exception as e:
                    # An uncaught exception has propogated down to our level - oh dear.
                    # Catch it, turn it into a 500, and return.
                    self.logger.exception("Unhandled exception in route `{}`:".format(repr(route)))
                    exc = HTTPException(500)
                    # Set the cause of the HTTP exception. Useful for 500 error handlers.
                    exc.__cause__ = e
                    # Set the route of the exception.
                    exc.route = route
                    self.log_request(ctx, 500)
                    await self.handle_http_error(exc, protocol, ctx)
                    return
                else:
                    # If there is no error happening, just log it as normal.
                    self.log_request(ctx, response.code)

                # Respond with the response.
                protocol.handle_resp(response)

                # Check if we should Keep-Alive it.
                if not ctx.request.should_keep_alive:
                    protocol.close()

    async def start(self, ip="0.0.0.0", port=4444, component=None):  # pragma: no cover
        """
        Run the Kyoukai component asynchronously.

        This bypasses Asphalt's runner completely and starts Kyoukai as it's own context.

        :param ip: The IP address to bind to.
        :param port: The port to bind to.
        :param component: The component to set on the application.
            If this is not passed in, it will create an empty one.
        """
        self.logger.warning("Kyoukai is bypassing Asphalt - contexts will not work.")
        ctx = Context()
        if not component:
            from kyoukai.asphalt import KyoukaiComponent
            self.component = KyoukaiComponent(self, ip, port)
        await self.component.start(ctx)

    def run(self, ip="0.0.0.0", port=4444, component=None):  # pragma: no cover
        """
        Runs the Kyoukai server from within your code.

        This is not normally invoked - instead Asphalt should invoke the Kyoukai component.
        However, this is here for convenience.
        """
        if not component:
            from kyoukai.asphalt import KyoukaiComponent
            component = KyoukaiComponent(self, ip, port)
        run_application(component)
