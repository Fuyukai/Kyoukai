"""
A Kyokai app is an app powered by libuv's event loop, and Kyokai's routing code.

This file contains the main definition for the app.
"""

import asyncio
import traceback

import uvloop
import logging

from kyokai.exc import HTTPClientException, HTTPException
from kyokai.request import Request
from kyokai.response import Response
from kyokai.route import Route
from .kanata import _KanataProtocol

# Enforce uvloop.
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

class Kyokai(object):
    """
    A Kyoukai app.
    """

    def __init__(self, name: str, log_level=logging.INFO):
        """
        Create a new app.

        Parameters:
            name: str
                The name of the app.

            log_level: The log level of the logger.
        """

        self.name = name
        self.loop = asyncio.get_event_loop()
        self.logger = logging.getLogger("Kyokai")
        self.logger.setLevel(log_level)

        self.routes = []
        self.error_handlers = {}

    def _kanata_factory(self, *args, **kwargs):
        return _KanataProtocol(self)

    async def _run(self, ip: str="127.0.0.1", port: int=4444):
        """
        Run the app. Internal coroutine.
        """
        print("Kyokai serving on {}:{}.".format(ip, port))
        self.logger.info("Kyokai serving on {}:{}.".format(ip, port))
        self.server = await self.loop.create_server(self._kanata_factory, ip, port)

    def run(self, ip: str="127.0.0.1", port: int=4444):
        """
        Run a Kyokai app.
        """
        self.loop.create_task(self._run(ip, port))
        try:
            self.loop.run_forever()
        except KeyboardInterrupt:
            return

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

    def route(self, regex, methods: list=None):
        """
        Create an incoming route for
        """
        if not methods:
            methods = ["GET"]
        r = Route(regex, methods)
        self.routes.append(r)
        return r

    def errorhandler(self, code: int):
        r = Route("", [])
        self.error_handlers[code] = r
        return r

    def _delegate_exc(self, protocol, request, error: HTTPException, body: str=None):
        """
        Internally delegates an exception, and responds appropriately.
        """
        # Check if there's a custom error handler, and if so, run it.
        if error.errcode in self.error_handlers:
            route = self.error_handlers[error.errcode]
            self.loop.create_task(self._invoke_errhandler(route, request, error, protocol))
        protocol.handle_resp(Response(error.errcode, error.errcode if not body else body, {}))

    def _delegate_response(self, protocol, request: Request):
        """
        Internally routes responses around.
        """
        # Match a route, if possible.
        self.logger.debug("Matching route `{}`.".format(request.path))
        coro = self._match_route(request.path, request.method)
        if not coro:
            # Match a 404.
            self.logger.info("{} - {} {}".format(404, request.method, request.path))
            self._delegate_exc(protocol, request, HTTPClientException(404, "Not Found"))
            return
        elif coro == -1:
            self.logger.info("{} - {} {}".format(405, request.method, request.path))
            self._delegate_exc(protocol, request, HTTPClientException(405, "Method Not Allowed"))
            return
        # Invoke the coroutine.
        self.loop.create_task(self._invoke(coro, request, protocol))

    async def _invoke_errhandler(self, route, request, error, protocol):
        """
        Invokes an error handler protocol, bypassing _delegate_exc.
        """
        try:
            response = await route.invoke(request)
        except Exception as e:
            if not isinstance(e, HTTPException):
                self.logger.error("Error in error handler {}:".format(route.__name__))
                traceback.print_exc()
                protocol.handle_resp(Response(500, "500 INTERNAL SERVER ERROR", {"X-Kyokai-Errorhandler":
                                                                                     route.__name__}))
            else:
                protocol.handle_resp(Response(e.errcode, e.msg, {}))
            return
        # Wrap response.
        response = self._wrap_response(response)
        protocol.handle_resp(response)

    async def _invoke(self, route, request, protocol: _KanataProtocol):
        """
        Invokes a function, if appropriate. Handles error automatically.
        """
        try:
            await self._wrapped_invoke(route, request, protocol)
        except Exception as e:
            if not isinstance(e, HTTPException):
                self.logger.error("Error in view {}:".format(route.__name__))
                traceback.print_exc()
                self._delegate_exc(protocol, request, HTTPException(500))
            else:
                self._delegate_exc(protocol, request, e)

    async def _wrapped_invoke(self, route, request, protocol: _KanataProtocol):
        """
        Invokes a route to run its code.
        """
        response = await route.invoke(request)
        # TODO: Wrap response better.
        response = self._wrap_response(response)
        self.logger.info("{} - {} {}".format(response.code, request.method, request.path))
        return protocol.handle_resp(response)