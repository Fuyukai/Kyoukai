"""
Asphalt framework mixin for Kyokai.
"""
import logging

import asyncio

from typeguard import check_argument_types

from kyokai.protocol import KyokaiProtocol
from asphalt.core import Component, resolve_reference, Context


class KyoukaiComponent(Component):
    def __init__(self, **config: dict):
        self._app = resolve_reference(config.get("app"))
        self.ip = config.pop("ip", "127.0.0.1")
        self.port = config.pop("port", 4444)

        self.loop = asyncio.get_event_loop()

        self.logger = logging.getLogger("Kyokai")

    def protocol_factory(self):
        """
        Return a new protocol
        """
        return KyokaiProtocol(self._app, self.context, HTTPRequestContext)

    async def start(self, ctx: Context):
        """
        Starts a Kyokai server.
        """
        self.context = ctx
        self.server = await self.loop.create_server(self.protocol_factory, self.ip, self.port)
        print("Kyoukai serving on {}:{}.".format(self.ip, self.port))
        self.logger.info("Kyokai serving on {}:{}.".format(self.ip, self.port))


class HTTPRequestContext(Context):
    """
    Sub-class of context used for HTTP requests.
    """
    def __init__(self, request, parent: Context):
        assert check_argument_types()
        super().__init__(parent=parent)
        self.request = request