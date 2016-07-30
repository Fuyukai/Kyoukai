import asyncio
import logging

from kyoukai.exc import HTTPException
from kyoukai.request import Request
from kyoukai.response import Response
from kyoukai.context import HTTPRequestContext


class KyokaiProtocol(asyncio.Protocol):
    """
    The Kyoukai protocol.
    """

    def __init__(self, app, parent_context):
        self.app = app
        self._transport = None
        self.ip = None
        self.client_port = None

        self.logger = logging.getLogger("Kyokai")

        self.loop = asyncio.get_event_loop()

        # Asphalt contexts
        self.parent_context = parent_context

        self.buffer = b""

    def connection_made(self, transport: asyncio.Transport):
        """
        Called when a connection is made, and is used to store the connection data.
        """
        self.ip, self.client_port = transport.get_extra_info("peername")
        self._transport = transport

        self.logger.debug("Recieved connection from {}:{}".format(*transport.get_extra_info("peername")))

    def handle_resp(self, res: Response):
        """
        Handle a response.

        :param res: The response to write into the transport.
        """
        data = res.to_bytes()
        self._transport.write(data)

    def data_received(self, data: bytes):
        """
        Create a new Request, and delegate Kyokai to process it.
        """
        self.logger.debug(
            "Recieved {} bytes of data from client {}:{}, feeding.".format(
                len(data), *self._transport.get_extra_info("peername")
            )
        )

        # Delegate as response.
        self.logger.debug("Delegating response for client {}:{}.".format(*self._transport.get_extra_info("peername")))
        # Create a request
        self.buffer += data
        req = Request()
        ctx = HTTPRequestContext(req, self.parent_context)
        try:
            req.parse(self.buffer, self.ip)
        except HTTPException as e:
            # Delegate the HTTP exception, probably a 400.
            self.app.log_request(e, code=400)
            self.loop.create_task(self.app.handle_http_error(e, self, ctx))
        else:
            if req.fully_parsed:
                # Reset buffer.
                self.logger.debug("Request for `{}` fully parsed, passing.".format(req.path))
                self.buffer = b""
                self.loop.create_task(self.app.delegate_request(self, ctx))
            else:
                # Continue.
                return

    def close(self):
        self._transport.close()
