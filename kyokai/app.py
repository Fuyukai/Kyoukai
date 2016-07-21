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
import magic
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

    #def register_blueprint(self, bp: Blueprint):
    #    """
    #    Registers a blueprint.
    #    """
    #    bp_routes = bp._init_bp()
    #    self.logger.info("Registered {} route(s) from blueprint `{}`.".format(len(bp_routes), bp._name))
    #    self.routes += bp_routes

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
                mimetype = magic.from_file(path, mime=True).decode()
            return Response(200, body=content.read(), headers={"Content-Type": mimetype})

    def _match_route(self, path, meth) -> typing.Tuple[int, Route]:
        """
        Match a route, based on the regular expression of the route.

        Returns a tuple:
             0 and the route if it's valid.
            -1 and the route if it's an invalid method.
            -2 and None if it doesn't match.
        """
        for route in self.routes:
            assert isinstance(route, Route), "Routes should be a Route class"
            if route.kyokai_match(path):
                if route.kyokai_method_allowed(meth):
                    return 0, route
                else:
                    return -1, route
        return -2, None

    def _wrap_response(self, response):
        """
        Wrap up a response, if applicable.

        This allows Flask-like `return ""`.
        """
        if isinstance(response, tuple):
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
        r = Route("", [])
        self.error_handlers[code] = r
        return r

    def before_request(self, func):
        """
        Adds a hook to run before request.
        """
        self.request_hooks["pre"].append(func)
        return func

    def after_request(self, func):
        """
        Adds a hook to run after the request.
        """
        self.request_hooks["post"].append(func)
        return func

    async def delegate_request(self, protocol, ctx: HTTPRequestContext):
        """
        Delegates a request to be handled automatically.
        """
        # Needs more indentation.
        async with ctx:
            self.logger.debug("Matching route `{}`.".format(ctx.request.path))
            coro = self._match_route(ctx.request.path, ctx.request.method)
            if coro[0] == -1:
                # 415 invalid method
                self.logger.info("{} {} - {}".format(ctx.request.method, ctx.request.path, 415))
                await self._exception_handler(protocol, ctx, coro[1], 415)
                return
            elif coro[0] == -2:
                self.logger.info("{} {} - {}".format(ctx.request.method, ctx.request.path, 404))
                await self._exception_handler(protocol, ctx, None, 404)
                return
            else:
                coro = coro[1]
            # Pre-request hooks.
            for hook in self.request_hooks["pre"]:
                ctx.request = await hook(ctx)
                if not ctx.request or not isinstance(ctx.request, Request):
                    self.logger.error("Error in pre-request hook {} - did not return a Request!".format(hook.__name__))
                    await self._exception_handler(protocol, ctx, None, 500)
                    return

            # Invoke the route, wrapped.
            try:
                response = await coro.invoke(ctx)
            except HTTPException as e:
                self.logger.info("{} {} - {}".format(ctx.request.method, ctx.request.path, e.errcode))
                await self._exception_handler(protocol, ctx, coro, e.errcode)
                return
            except Exception as e:
                self.logger.info("{} {} - 500".format(ctx.request.method, ctx.request.path))
                self.logger.error("Error in route {}".format(coro.__name__))
                traceback.print_exc()
                if self.debug:
                    r = Response(500, traceback.format_exc())
                    protocol.handle_resp(r)
                    return
                await self._exception_handler(protocol, ctx, coro, 500)
                return

            # Wrap the response.
            response = self._wrap_response(response)
            # Post-request hooks.
            for hook in self.request_hooks["post"]:
                response = await hook(response)
                if not response:
                    self.logger.error("Error in post-request hook {} - did not return anything!".format(hook.__name__))
                    await self._exception_handler(protocol, ctx, None, 500)
                    return

            self.logger.info("{} {} - {}".format(ctx.request.method, ctx.request.path, response.code))
            # Handle the response.
            protocol.handle_resp(response)
            # Check if we should close it.
            if ctx.request.headers.get("Connection") != "keep-alive":
                # Close the conenction.
                protocol.close()

    def _get_errorhandler(self, coro: Route, code: int):
        """
        Gets the error handler for the route.

        Used for per-blueprint routes.
        """
        if not coro:
            return self.error_handlers.get(code)
        else:
            r_handler = coro.get_errorhandler(code)
            return r_handler if r_handler else self.error_handlers.get(code)

    async def _exception_handler(self, protocol, ctx: HTTPRequestContext, coro: typing.Union[Route, None], code):
        """
        Handles built in HTTP exceptions.
        """
        route = self._get_errorhandler(coro, code)
        if route:
            # Await the invoke.
            try:
                response = await route.invoke(ctx)
                response = self._wrap_response(response)
            except Exception:
                self.logger.error("Error in error handler for code {}".format(code))
                traceback.print_exc()
                if self.debug:
                    response = Response(500, traceback.format_exc())
                else:
                    response = Response(500, "500 Internal Server Error", {})
        else:
            response = Response(code, body=str(code))

        # Handle the response.
        protocol.handle_resp(response)

        # Check if we should close it.
        # Check if we have headers, because these don't exist in a 400 from the protocol.
        if hasattr(ctx.request, "headers"):
            if ctx.request.headers.get("Connection") != "keep-alive":
                # Close the conenction.
                protocol.close()
        else:
            protocol.close()

    async def start(self, ip="0.0.0.0", port=4444, component=None):
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

    def run(self, ip="0.0.0.0", port=4444, component=None):
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
