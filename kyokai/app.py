"""
A Kyokai app is an app powered by libuv's event loop, and Kyokai's routing code.

This file contains the main definition for the app.
"""

import asyncio
import io
import mimetypes
import os
import traceback
import logging
import typing
try:
    import magic
except (ImportError, OSError):
    _has_magic = False
else:
    _has_magic = True
from asphalt.core import Context

from asphalt.core.runner import run_application
from typeguard import check_argument_types

from kyokai.blueprints import Blueprint
from kyokai.context import HTTPRequestContext
from kyokai.util import static_filename

from kyokai.exc import HTTPClientException, HTTPException
from kyokai.request import Request
from kyokai.response import Response
from kyokai.route import Route

try:
    from kyokai.renderers import MakoRenderer as MakoRenderer

    _has_mako = True
except ImportError:
    _has_mako = False

try:
    from kyokai.renderers import JinjaRenderer as JinjaRenderer

    _has_jinja2 = True
except ImportError:
    _has_jinja2 = False


class Kyōkai(object):
    """
    A Kyoukai app.
    """

    def __init__(self, name: str, cfg: dict = None):
        """
        Create a new app.

        Parameters:
            name: str
                The name of the app.
        """

        self.name = name
        self.loop = asyncio.get_event_loop()

        self.logger = logging.getLogger("Kyokai")

        self.error_handlers = {}

        self.config = cfg if cfg else {}
        self.request_hooks = {
            "pre": [],
            "post": []
        }

        # Define the "root" blueprint, which is used for @app.request.
        self._root_bp = Blueprint("root", None)

        self.debug = False

    def reconfigure(self, config: dict):
        self.config = {**config, **self.config}
        # Should we use logging speedhack?
        # This speeds up Kyoukai MASSIVELY - 0.3ms off each request, which is around 75% on an empty request.
        if self.config.get("use_logging_speedhack"):
            print("Using logging speed hack.")

            class _FakeLogging(logging.Logger):
                def isEnabledFor(self, level):
                    return False

            logging.Logger.manager.loggerDict["Kyokai"] = _FakeLogging("Kyokai")

        # Create a renderer.
        if self.config.get("template_renderer") == "mako":
            if not _has_mako:
                raise ImportError("Mako is not installed; cannot use for templates.")
            else:
                self._renderer = MakoRenderer.render
        elif self.config.get("template_renderer") == "jinja2":
            if not _has_jinja2:
                raise ImportError("Jinja2 is not installed; cannot use for templates.")
            else:
                self._renderer = JinjaRenderer.render

        if self.config.get("debug") is True:
            self.debug = True

    def register_blueprint(self, bp: Blueprint):
        """
        Registers a blueprint as a sub-blueprint to the root blueprint.
        """
        assert check_argument_types()
        self._root_bp.add_child(bp)
        if bp.parent is None:
            bp.parent = self._root_bp
        return bp

    def render(self, filename, **kwargs):
        """
        Render a template using the specified rendering engine.
        """
        return self._renderer(filename, **kwargs)

    def get_static_path(self, filename: str) -> str:
        """
        Gets a sanitized static path.

        The file is not guarenteed to exist.
        """
        return os.path.join(os.getcwd(), self.config.get("static_dir", "static"), static_filename(filename))

    def get_static_file(self, filename: str) -> io.BufferedIOBase:
        """
        Gets a file, safely.

        Sanitizes the input, then opens `static/f`, or None if the file does not exist.
        """
        fname = self.get_static_path(filename)
        if not os.path.exists(fname):
            return None
        else:
            return open(os.path.join(os.getcwd(), self.config.get("static_dir", "static"), fname), 'r')

    def get_static(self, filename: str) -> Response:
        """
        Gets a file, using static, but returns a Response instead of the file handle.
        """
        content = self.get_static_file(filename)
        if not content:
            raise HTTPClientException(404)

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

        Returns the route if it's valid, None if it's not, and raises a 405 HTTPException if it's a bad method for
        the specified route.
        """
        return self._root_bp.match(path, meth)

    def _wrap_response(self, response):
        """
        Wrap up a response, if applicable.

        This allows Flask-like `return ""`.
        """
        if response is None:
            r = Response(204, "", {})
        elif isinstance(response, tuple):
            if len(response) == 1:
                # Only body.
                r = Response(200, response[0], {})
            elif len(response) == 2:
                # Body and code.
                r = Response(response[1], response[0], {})
            elif len(response) == 3:
                # Body, code, headers.
                r = Response(response[1], response[0], response[2])
            else:
                # what
                raise HTTPException
        elif isinstance(response, Response):
            r = response
        else:

            r = Response(200, response, {})
        return r

    def route(self, regex, methods: list = None, hard_match: bool = False):
        """
        Create an incoming route for a function.

        Parameters:
            regex:
                The regular expression to match the path to.
                In standard Python `re` forme.

                Group matches are automatically extracted from the regex, and passed as arguments.

            methods:
                The list of allowed methods, e.g ["GET", "POST"].
                You can check the method with `request.method`.

            hard_match:
                Should we match based on equality, rather than regex?

                This prevents index or lower level paths from matching 404s at higher levels.
        """
        # Rewrite it to the _root_bp method.
        return self._root_bp.route(regex, methods, hard_match)

    def errorhandler(self, code: int):
        """
        Create an error handler for the specified code.

        This will wrap the function in a Route.
        """
        return self._root_bp.errorhandler(code)

    def log_request(self, ctx: HTTPRequestContext, code: int = 200):
        """
        Logs a request to the logger.
        """
        try:
            route = ctx.request.path
        except AttributeError:
            # *really* bad request - ignore it.
            return
        self.logger.info("{} {} - {}".format(ctx.request.method, route, code))

    def before_request(self, func):
        """
        Adds a hook to run before request.
        """
        return self._root_bp.before_request(func)

    def after_request(self, func):
        """
        Adds a hook to run after the request.
        """
        return self._root_bp.after_request(func)

    async def _handle_http_error(self, err: HTTPException, protocol, ctx: HTTPRequestContext):
        """
        Handles HTTP errors.
        """
        code = err.errcode
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
            if err.errcode == 500 and self.debug:
                body = traceback.format_exc()
            else:
                body = str(code)
            resp = Response(code, body, {"Content-Type": "text/plain"})
        else:
            # Invoke the error handler specified.
            resp = self._wrap_response(await error_handler.invoke(self, ctx))
        protocol.handle_resp(resp)

        # Check if we should close the connection.
        if hasattr(ctx.request, "headers"):
            # The hasattr check is required because in a 400, the request is bad and doesn't have headers.
            if ctx.request.headers.get("connection") != "keep-alive":
                protocol.close()
        else:
            # If it's that bad, just close it anyway.
            protocol.close()

        return resp

    async def delegate_request(self, protocol, ctx: HTTPRequestContext):
        """
        Handles a request from the protocol.
        """
        async with ctx:
            # First, try and match the route.
            try:
                route = self._match_route(ctx.request.path, ctx.request.method)
            except HTTPException as e:
                # We matched it; but the route doesn't work for this method.
                # So we catch the 405 error,
                if e.errcode == 405:
                    self.log_request(ctx, code=e.errcode)
                    response = await self._handle_http_error(e, protocol, ctx)
                    return
                else:
                    self.logger.error("??????? Something went terribly wrong.")
                    return

            # If the route did not match, return a 404.
            if not route:
                fof = HTTPException(404)
                self.log_request(ctx, code=404)
                await self._handle_http_error(fof, protocol, ctx)
                return

            # Try and invoke the Route.
            try:
                # Note that this will already be a Response.
                # The route should call `app._wrap_response` when handling the response.
                # This is because routes are responsible for pre-route and post-route hooks, calling them in the
                # blueprint as appropriate.
                # So we just pass ourselves to the route and hope it invokes properly.
                response = await route.invoke(self, ctx)
            except HTTPException as e:
                # Handle a HTTPException normally.
                self.log_request(ctx, e.errcode)
                await self._handle_http_error(e, protocol, ctx)
                return
            except Exception as e:
                # An uncaught exception has propogated down to our level - oh dear.
                # Catch it, turn it into a 500, and return.
                self.logger.exception("Unhandled exception in route:")
                exc = HTTPException(500)
                self.log_request(ctx, 500)
                await self._handle_http_error(exc, protocol, ctx)
                return
            else:
                self.log_request(ctx, response.code)

            # Respond with the response.
            protocol.handle_resp(response)

            # Copy/pasted, but it doesn't really matter.
            # Check if we should close the conn.
            if hasattr(ctx.request, "headers"):
                # The hasattr check is required because in a 400, the request is bad and doesn't have headers.
                if ctx.request.headers.get("connection") != "keep-alive":
                    protocol.close()
            else:
                # If it's that bad, just close it anyway.
                protocol.close()

    async def start(self, ip = "0.0.0.0", port = 4444, component = None):
        """
        Run the Kyoukai component asynchronously.

        This bypasses Asphalt's runner completely and starts Kyoukai as it's own context.
        """
        self.logger.warning("Kyoukai is bypassing Asphalt - contexts will not work.")
        ctx = Context()
        if not component:
            from kyokai.asphalt import KyoukaiComponent
            self.component = KyoukaiComponent(self, ip, port)
        await self.component.start(ctx)

    def run(self, ip = "0.0.0.0", port = 4444, component = None):
        """
        Runs the Kyoukai server from within your code.

        Note that

        This is not normally invoked - instead Asphalt should invoke the Kyoukai component.
        However, this is here for convenience.
        """
        if not component:
            from kyokai.asphalt import KyoukaiComponent
            component = KyoukaiComponent(self, ip, port)
        run_application(component)


# Alias it
Kyokai = Kyōkai
Kyoukai = Kyokai
