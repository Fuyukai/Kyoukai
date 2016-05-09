"""
Kanata is the Kyokai protocol, used for handling the events of a Kyokai server.

Each Kanata handles an individual connection.
"""
import asyncio
import logging

from kyokai.exc import HTTPException
from kyokai.request import Request

logger = logging.getLogger("Kyokai")


class _KanataProtocol(asyncio.Protocol):
    """
    A Kanata protocol.
    """
    def __init__(self, app):
        self.app = app
        self._transport = None
        self.ip = None
        self.client_port = None

        self.buffer = b""

    def connection_made(self, transport: asyncio.Transport):
        """
        Set the appropriate self vals.
        """
        self.ip, self.client_port = transport.get_extra_info("peername")
        self._transport = transport

        logger.debug("Recieved connection from {}:{}".format(*transport.get_extra_info("peername")))

    def data_received(self, data: bytes):
        """
        Create a new Request, and delegate Kyokai to process it.
        """
        logger.debug("Recieved {} bytes of data from client {}:{}, feeding into the buffer.."
                     .format(len(data), *self._transport.get_extra_info("peername"))
                     )
        # Feed into the buffer.

        if data:
            self.buffer += data
        # TODO: Less shitty detection of EOF.
        if self.buffer.endswith(b"\r\n\r\n"):
            # Delegate as response.
            logger.debug("Delegating response for client {}:{}.".format(*self._transport.get_extra_info("peername")))
            buf = self.buffer
            self.buffer = b""
            # Create a request
            try:
                req = Request.from_data(buf)
            except HTTPException as e:
                # Delegate the HTTP exception, probably a 400.
                self.app._delegate_exc(self, e)
            else:
                self.app._delegate_response(self, req)