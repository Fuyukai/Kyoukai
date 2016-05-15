"""
A Kyokai app is an app powered by libuv's event loop, and Kyokai's routing code.

This file contains the main definition for the app.
"""

import asyncio
import io
import os
import traceback
import logging

import magic
import yaml

from kyokai.blueprints import Blueprint
from kyokai.context import HTTPRequestContext

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader as Loader

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

    def __init__(self, name: str, cfg: dict=None):
        """
        Create a new app.

        Parameters:
            name: str
                The name of the app.

            log_level:
                The log level of the logger.

        """

        self.name = name
        self.loop = asyncio.get_event_loop()

        self.routes = []
        self.error_handlers = {}

        self.config = cfg if cfg else {}
        self.request_hooks = {
            "pre": [],
            "post": []
        }

    def reconfigure(self, config: dict):
        # Should we use logging speedhack?
        # This speeds up Kyoukai MASSIVELY - 0.3ms off each request, which is around 75% on an empty request.
        if self.config.get("use_logging_speedhack"):
            print("Using logging speed hack.")

            class _FakeLogging(logging.Logger):
                def isEnabledFor(self, level):
                    return False

            logging.Logger.manager.loggerDict["Kyokai"] = _FakeLogging("Kyokai")

        self.logger = logging.getLogger("Kyokai")

        # Create a renderer.
        if self.config.get("template_renderer", "mako") == "mako":
            if not _has_mako:
                raise ImportError("Mako is not installed; cannot use for templates.")
            else:
                self._renderer = MakoRenderer.render
        elif self.config.get("template_renderer", "mako") == "jinja2":
            if not _has_jinja2:
                raise ImportError("Jinja2 is not installed; cannot use for templates.")
            else:
                self._renderer = JinjaRenderer.render


    def register_blueprint(self, bp: Blueprint):
        """
        Registers a blueprint.
        """
        self.routes += bp._init_bp()

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
        keepcharacters = (' ', '.', '_')
        fname = "".join(c for c in filename if c.isalnum() or c in keepcharacters).rstrip()
        return os.path.join(os.getcwd(), self.config.get("static_dir", "static"), fname)

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
            mimetype = magic.from_file(self.get_static_path(filename), mime=True)
            return Response(200, body=content.read(), headers={"Content-Type": mimetype.decode()})

    def _match_route(self, path, meth):
        """
        Match a route, based on the regular expression of the route.
        """
        for route in self.routes:
            assert isinstance(route, Route), "Routes should be a Route class"
            if route.kyokai_match(path):
                if route.kyokai_method_allowed(meth):
                    return route
                else:
                    return -1

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
        if not methods:
            methods = ["GET"]
        # Override hard match if it's a `/` route.
        if regex == "/":
            hard_match = True
        r = Route(regex, methods, hard_match)
        self.routes.append(r)
        return r

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
            if coro == -1:
                # 415 invalid method
                self.logger.info("{} {} - {}".format(ctx.request.method, ctx.request.path, 415))
                await self._exception_handler(protocol, ctx.request, 415)
                return
            elif not coro:
                self.logger.info("{} {} - {}".format(ctx.request.method, ctx.request.path, 404))
                await self._exception_handler(protocol, ctx.request, 404)
                return

            # Pre-request hooks.
            for hook in self.request_hooks["pre"]:
                ctx.request = await hook(ctx)
                if not ctx.request or not isinstance(ctx.request, Request):
                    self.logger.error("Error in pre-request hook {} - did not return a Request!".format(hook.__name__))
                    await self._exception_handler(protocol, ctx.request, 500)
                    return

            # Invoke the route, wrapped.
            try:
                response = await coro.invoke(ctx)
            except HTTPException as e:
                self.logger.info("{} {} - {}".format(ctx.request.method, ctx.request.path, e.errcode))
                await self._exception_handler(protocol, ctx, e.errcode)
                return
            except Exception as e:
                self.logger.info("{} {} - 500".format(ctx.request.method, ctx.request.path))
                self.logger.error("Error in route {}".format(coro.__name__))
                traceback.print_exc()
                await self._exception_handler(protocol, ctx, 500)
                return

            # Wrap the response.
            response = self._wrap_response(response)
            # Post-request hooks.
            for hook in self.request_hooks["post"]:
                response = await hook(response)
                if not response:
                    self.logger.error("Error in post-request hook {} - did not return anything!".format(hook.__name__))
                    await self._exception_handler(protocol, ctx, 500)
                    return

            self.logger.info("{} {} - {}".format(ctx.request.method, ctx.request.path, response.code))
            # Handle the response.
            protocol.handle_resp(response)
            # Check if we should close it.
            if ctx.request.headers.get("Connection") != "keep-alive":
                # Close the conenction.
                protocol.close()

    async def _exception_handler(self, protocol, ctx: HTTPRequestContext, code):
        """
        Handles built in HTTP exceptions.
        """
        if code in self.error_handlers:
            route = self.error_handlers[code]
            # Await the invoke.
            try:
                response = await route.invoke(ctx)
                response = self._wrap_response(response)
            except Exception:
                self.logger.error("Error in error handler for code {}".format(code))
                traceback.print_exc()
                response = Response(500, "500 Internal Server Error", {})
        else:
            response = Response(code, body=str(code))

        # Handle the response.
        protocol.handle_resp(response)

        # Check if we should close it.
        if ctx.request.headers.get("Connection") != "keep-alive":
            # Close the conenction.
            protocol.close()


# Alias it
Kyokai = Kyōkai
