"""
A Kyokai app is an app powered by libuv's event loop, and Kyokai's routing code.

This file contains the main definition for the app.
"""

import asyncio
import uvloop
import logging

from kyokai.request import Request
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

    def _delegate_exc(self, protocol):
        pass

    def _delegate_response(self, protocol, request: Request):
        """
        Internally routes responses around.
        """
