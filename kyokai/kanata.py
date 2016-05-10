"""
Kanata is the Kyokai protocol, used for handling the events of a Kyokai server.

Each Kanata handles an individual connection.
"""
import asyncio
import logging

from kyokai.exc import HTTPException
from kyokai.request import Request
from kyokai.response import Response

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

    def handle_resp(self, res: Response):
        """
        Handle a response.

        Sends the Response to the client.
        """
        data = res.to_bytes()
        self._transport.write(data)

    def data_received(self, data: bytes):
        """
        Create a new Request, and delegate Kyokai to process it.
        """
        logger.debug("Recieved {} bytes of data from client {}:{}, feeding."
                     .format(len(data), *self._transport.get_extra_info("peername"))
                     )

        # Delegate as response.
        logger.debug("Delegating response for client {}:{}.".format(*self._transport.get_extra_info("peername")))
        # Create a request
        self.buffer += data
        try:
            req = Request.from_data(self.buffer)
        except HTTPException as e:
            # Delegate the HTTP exception, probably a 400.
            self.app._delegate_exc(self, e)
        else:
            if req._fully_parsed:
                # Reset buffer.
                self.buffer = b""
                self.app._delegate_response(self, req)
            else:
                # Continue.
                return

    def close(self):
        self._transport.close()