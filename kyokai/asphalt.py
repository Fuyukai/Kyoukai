"""
Asphalt framework mixin for Kyokai.
"""
import logging

import asyncio
from typing import Union

from typeguard import check_argument_types

from kyokai.protocol import KyokaiProtocol

from asphalt.core import Component, resolve_reference, Context

loop = asyncio.get_event_loop()
logger = logging.getLogger("Kyokai")


class KyoukaiComponent(Component):
    def __init__(self, app, ip: str = '0.0.0.0', port: int = 4444):
        self._app = resolve_reference(app)
        self.ip = ip
        self.port = port

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
        self.server = await loop.create_server(self.protocol_factory, self.ip, self.port)
        print("Kyoukai serving on {}:{}.".format(self.ip, self.port))
        logger.info("Kyokai serving on {}:{}.".format(self.ip, self.port))


class HTTPRequestContext(Context):
    """
    Sub-class of context used for HTTP requests.
    """

    def __init__(self, request, parent: Context):
        assert check_argument_types()
        super().__init__(parent=parent)
        self.request = request
