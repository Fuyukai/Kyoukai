"""
A Kyokai app is an app powered by libuv's event loop, and Kyokai's routing code.

This file contains the main definition for the app.
"""

import asyncio
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

        self.routes = []

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
            if route.kyokai_match(path, meth):
                return route

    def route(self, regex, methods: list=list("GET")):
        """
        Create an incoming route for
        """
        r = Route(regex, methods)
        self.routes.append(r)
        return r

    def _delegate_exc(self, protocol, error: HTTPException):
        """
        Internally delegates an exception, and responds appropriately.
        """
        # TODO: Add custom exception handlers.
        protocol.handle_resp(Response(error.errcode, error.errcode, {}))

    def _delegate_response(self, protocol, request: Request):
        """
        Internally routes responses around.
        """
        # Match a route, if possible.
        self.logger.debug("Matching route `{}`.".format(request.path))
        coro = self._match_route(request.path, request.method)
        if not coro:
            # Match a 404.
            self._delegate_exc(protocol, HTTPClientException(404, "Not Found"))
            return
        # Invoke the coroutine.
        self.loop.create_task(self._invoke(coro, request, protocol))

    async def _invoke(self, route, request, protocol: _KanataProtocol):
        """
        Invokes a route to run its code.
        """
        try:
            response = await route.invoke(request)
        except HTTPException as e:
            self._delegate_exc(protocol, e)