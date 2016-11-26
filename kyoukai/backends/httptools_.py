"""
The default HTTPTools backend for Kyoukai.
"""
import asyncio
import logging
import traceback
import warnings
from io import BytesIO

import chardet
import httptools
from asphalt.core import Context
from werkzeug.wrappers import Request, Response

from kyoukai.wsgi import to_wsgi_environment, get_formatted_response

CRITICAL_ERROR_TEXT = """HTTP/1.0 500 INTERNAL SERVER ERROR
Server: Kyoukai
X-Powered-By: Kyoukai
Content-Type: text/html; charset=utf-8
Content-Length: 310

<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">
<title>Critical Server Error</title>
<h1>Critical Server Error</h1>
<p>An unrecoverable error has occurred within Kyoukai.
If you are the developer, please report this at <a href="https://github.com/SunDwarf/Kyoukai">the Kyoukai issue
tracker.</a>
""".replace("\n", "\r\n")


class KyoukaiProtocol(asyncio.Protocol):
    """
    The base protocol for Kyoukai using httptools for a HTTP/1.0 or HTTP/1.1 interface.
    """

    def __init__(self, app: 'Kyoukai', parent_context: Context,
                 server_ip: str, server_port: int):
        """
        :param app: The application associated with this request.
        :param parent_context: The parent context for this request.
            A new HTTPRequestContext will be derived from this.
        """

        self.app = app
        self.parent_context = parent_context

        self.server_ip = server_ip
        self.server_port = server_port

        # Transport.
        # This is written to by our request when it's done.
        self.transport = None  # type: asyncio.WriteTransport

        # Request lock.
        # This ensures that requests are processed serially, and responded to in the correct order, as the lock is
        # released after processing a request completely.
        self.lock = asyncio.Lock()

        # Parser event.
        # Set when the http parser is ready to hand over the new request to Kyoukai.
        self.parser_ready = asyncio.Event()

        # The parser itself.
        # This is created per connection, and uses our own class.
        self.parser = httptools.HttpRequestParser(self)

        # A waiter that 'waits' on the event to clear.
        # Once the wait is over, it then delegates the request to the app.
        self.waiter = None  # type: asyncio.Task

        # The IP and port of the client.
        self.ip, self.client_port = None, None

        # Intermediary data storage.
        self.headers = {}
        self.body = BytesIO()
        self.full_url = ""

        self.loop = asyncio.get_event_loop()
        self.logger = logging.getLogger("Kyoukai")

    # httptools callbacks
    def on_message_begin(self):
        """
        Called when a message begins.
        """
        self.body = BytesIO()
        self.headers = {}
        self.full_url = ""

    def on_header(self, name: bytes, value: bytes):
        """
        Called when a header has been received.

        :param name: The name of the header.
        :param value: The value of the header.
        """
        self.headers[name.decode()] = value.decode()

    def on_body(self, body: bytes):
        """
        Called when part of the body has been received.

        :param body: The body text.
        """
        self.body.write(body)

    def on_url(self, url: bytes):
        """
        Called when a URL is received from the client.
        """
        self.full_url = url.decode("utf-8")

    def on_message_complete(self):
        """
        Called when a message is complete.
        This calls the event set() to ensure the protocol continues on with parsing.
        """
        self.parser_ready.set()

    # asyncio procs
    def connection_made(self, transport: asyncio.WriteTransport):
        """
        Called when a connection is made via asyncio.

        :param transport: The transport this is using.
        """
        try:
            self.ip, self.client_port = transport.get_extra_info("peername")
        except ValueError:
            # Sometimes socket.socket.getpeername() isn't available, so it tried to unpack a None.
            # Or, it returns None (wtf?)
            # So just provide some fake values.
            warnings.warn("getpeername() returned None, cannot provide transport information.")
            self.ip, self.client_port = None, None

        self.transport = transport

    def data_received(self, data: bytes):
        """
        Called when data is received into the connection.
        """
        # Feed it into the parser, and handle any errors that might happen.
        try:
            self.parser.feed_data(data)
        except httptools.HttpParserInvalidMethodError:
            # TODO: Exceptions
            raise
        except httptools.HttpParserError:
            raise

        # Create an event waiter.
        if self.waiter is None:
            self.waiter = self.loop.create_task(self._wait_wrapper())

    # kyoukai handling
    async def _wait_wrapper(self):
        try:
            await self._wait()
        except:
            self.logger.critical("Error in Kyoukai's HTTP handling!")
            traceback.print_exc()
            self._raw_write(CRITICAL_ERROR_TEXT.encode())
            self.close()
        finally:
            self.waiter.cancel()
            self.waiter = None

    async def _wait(self):
        """
        The main core of the protocol.

        This constructs a new Werkzeug request from the headers.
        """
        await self.parser_ready.wait()

        # Event is set, construct the new fake WSGI environment

        # Check if the body has data in it by asking it to tell us what position it's seeked to.
        # If it's > 0, it has data, so we can use it. Otherwise, it doesn't, so it's useless.
        if self.body.tell():
            self.body.seek(0)
            body = self.body
        else:
            body = None

        version = self.parser.get_http_version()
        method = self.parser.get_method().decode()

        new_environ = to_wsgi_environment(headers=self.headers, method=method, path=self.full_url,
                                          http_version=version, body=body)

        new_environ["kyoukai.protocol"] = self
        new_environ["SERVER_NAME"] = self.server_ip
        new_environ["SERVER_PORT"] = str(self.server_port)

        # Construct a Request object.
        new_r = Request(new_environ, False)

        # Invoke the app.
        try:
            result = await self.app.process_request(new_r, self.parent_context)
        except Exception:
            # not good!
            # write the scary exception text
            self.logger.exception("Error in Kyoukai request handling!")
            self._raw_write(CRITICAL_ERROR_TEXT.encode("utf-8"))
            return
        else:
            # Write the response.
            self.write_response(result, new_environ)
        finally:
            if not self.parser.should_keep_alive():
                self.close()
            # unlock the event and remove the waiter
            self.parser_ready.clear()
            self.parser = httptools.HttpRequestParser(self)

    # transport methods
    def close(self):
        return self.transport.close()

    def write_response(self, response: Response, fake_environ: dict):
        """
        Writes a Werkzeug response to the transport.
        """
        return self.raw_write(get_formatted_response(response, fake_environ))

    def write(self, data: str):
        """
        Writes data to the socket.
        """
        d = data.encode()
        return self.raw_write(d)

    def raw_write(self, data: bytes):
        """
        Writes data to the transport.
        """
        return self._raw_write(data)

    def _raw_write(self, data: bytes):
        """
        Does a raw write to the underlying transport, if we can.

        :param data: The data to write.
        """
        try:
            self.transport.write(data)
        except OSError:
            # connection might be closed...
            # just ignore it.
            return
