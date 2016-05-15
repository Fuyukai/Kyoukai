"""
Asphalt framework mixin for Kyokai.
"""
import logging

import asyncio
from functools import partial
from typing import Union

from asphalt.core import Component, resolve_reference, Context
from typeguard import check_argument_types

from kyokai.app import Kyokai
from kyokai.protocol import KyokaiProtocol

logger = logging.getLogger("Kyokai")


class KyoukaiComponent(Component):
    def __init__(self, app: Union[str, Kyokai], ip: str = '0.0.0.0', port: int = 4444):
        assert check_argument_types()
        self.app = resolve_reference(app)
        self.ip = ip
        self.port = port

    async def start(self, ctx: Context):
        """
        Starts a Kyokai server.
        """
        protocol_factory = partial(KyokaiProtocol, self.app, ctx)
        server = await get_event_loop().create_server(protocol_factory)
        logger.info("Kyokai serving on {}:{}.".format(self.ip, self.port))
