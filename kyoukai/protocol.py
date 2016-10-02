"""
httptools based HTTP protocol.
"""
import asyncio
import logging
import traceback

import httptools

from kyoukai.request import Request
from kyoukai.response import Response
from kyoukai.exc import HTTPException, exc_from
from kyoukai.context import HTTPRequestContext

CRITICAL_ERROR_TEXT = """HTTP/1.0 500 INTERNAL SERVER ERROR
Server: Kyoukai
X-Powered-By: Kyoukai
Content-Type: text/html; charset=utf-8

<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">
<title>Critical Server Error</title>
<h1>Critical Server Error</h1>
<p>An unrecoverable error has occurred within Kyoukai.
If you are the developer, please report this at <a href="https://github.com/SunDwarf/Kyoukai">the Kyoukai issue
tracker.</a>
""".replace("\n", "\r\n")


class HTTPToolsHandler:  # pragma: no cover
    """
    A callback handler that works with the HTTPTools library.

    This class does some downright horrible things in order to be compatible with httptool's weird mix of callbacks
    and normal functions, involving asyncio events.
    """

    def __init__(self, protocol: 'KyoukaiProtocol'):
        self.protocol = protocol

        # This defines the current request.
        self.current_request = None

    def reset(self):
        """
        Resets the current request.
        Should be called after the message is complete.
        """
        self.current_request = None

    def on_message_begin(self):
        """
        Called when a message has begun.

        This creates the new Request.
        """
        self.current_request = self.protocol.app.request_cls()

    def on_header(self, name: bytes, value: bytes):
        """
        Called when a header is set.
        """
        # Decode the name and the values to get the header.
        self.current_request.headers[name.decode()] = value.decode()

    def on_body(self, body: bytes):
        """
        Called when the body is received.

        This sets self.current_request.body.
        """
        self.current_request.body += body.decode()

    def on_url(self, url: bytes):
        """
        Called when a URL is recieved.

        This is undocumented in the HTTPTools README.
        """
        self.current_request.full_path = url

    def on_message_complete(self):
        """
        Called when a message is complete.

        This calls the event set() to ensure the protocol continues on with parsing.
        """
        self.protocol.parser_ready.set()


class KyoukaiProtocol(asyncio.Protocol):  # pragma: no cover
    """
    The Kyoukai protocol.
    """

    def __init__(self, app, parent_context):
        self.app = app
        self._transport = None
        self.ip = None
        self.client_port = None

        self.logger = logging.getLogger("Kyoukai")

        self.loop = asyncio.get_event_loop()

        # Asphalt contexts
        self.parent_context = parent_context

        # Request lock.
        # This ensures that requests are processed serially, and responded to in the correct order, as the lock is
        # released after processing a request completely.
        self.lock = asyncio.Lock()

        # Parser event.
        # Set when the HTTPTools parser is ready to hand over the new request to Kyoukai.
        self.parser_ready = asyncio.Event()

        # The parser itself.
        # This is created per connection.
        self.parser_obb = HTTPToolsHandler(self)
        self.parser = httptools.HttpRequestParser(self.parser_obb)

        # Define a waiter, that 'waits' on the event to clear.
        # Once the wait is over, it then delegates the request.
        self.waiter = None

    async def _safe_handle_error(self, context: HTTPRequestContext, exception: Exception):
        """
        "Safely" handle a HTTP exception.

        This is **only** called when Kyoukai fails to process a HTTP error.
        ``delegate_request`` safely attempts to process errors properly. If an error within Kyoukai happens,
        it will pass back down to this layer, which is very very bad.

        This first calls ``app.handle_http_exception``.
        If that fails, it sends the critical error text.

        :param exception: The exception to send down the line.
        :return:
        """
        self.logger.warning("Exception happened during HTTP parsing.")
        self.logger.warning("This is not necessarily a bug.")
        traceback.print_exc()
        # Convert the exception.
        new_e = exc_from(exception)
        try:
            await self.app.handle_http_error(new_e, self, context)
        except Exception:
            # Critical error.
            self.logger.critical("Unhandled exception inside Kyoukai, when processing a HTTP error!")
            self.logger.critical("This is a bug. Please report it!")
            self.logger.critical("".join(traceback.format_exc()))
            self.write(CRITICAL_ERROR_TEXT.encode())
            self.close()

    def reset(self):
        """
        Resets the HTTP parser.
        """
        self.parser_obb.reset()
        # Reset the current protocol.
        self.parser = httptools.HttpRequestParser(self.parser_obb)

    async def _wait(self):
        """
        Waits for the request to be ready.
        :return:
        """
        await self.parser_ready.wait()
        # Remove the current waiter.
        self.waiter = None
        # Unset the event. We're ready to begin processing.
        self.parser_ready.clear()

        # Take in the request, and call parse_all().
        request = self.parser_obb.current_request
        # Set a handful of properties manually.
        request.version = self.parser.get_http_version()
        request.method = self.parser.get_method().decode()
        request.should_keep_alive = self.parser.should_keep_alive()
        # Set the IP and the port on the request.
        request.ip = self.ip
        request.port = self.client_port
        # Create the new HTTPRequestContext.
        ctx = HTTPRequestContext(request, self.app, self.parent_context)
        # Parse all fields in the Exception.
        try:
            request.parse_all()
        except HTTPException as e:
            # Handle the HTTP exception.
            await self._safe_handle_error(ctx, e)
            return
        except Exception as e:
            await self._safe_handle_error(ctx, e)
            return
        finally:
            self.reset()

        # Reset the parser.
        self.parser_obb.reset()

        # Create the delegate_request task.
        try:
            await self.app.delegate_request(self, ctx)
        except Exception as exc:
            await self._safe_handle_error(ctx, exc)
        finally:
            self.reset()

    def connection_made(self, transport: asyncio.Transport):
        """
        Called when a connection is made, and is used to store the connection data.
        """
        self.ip, self.client_port = transport.get_extra_info("peername")
        self._transport = transport

        self.logger.debug("Recieved connection from {}:{}".format(*transport.get_extra_info("peername")))

    def connection_lost(self, exc):
        """
        Called when a connection is lost.
        """
        self._empty_state()

    def data_received(self, data: bytes):
        """
        Called when data is received.

        This is the bulk of the processing.
        """
        # Feed the data to the parser.
        try:
            self.parser.feed_data(data)
        except httptools.HttpParserInvalidMethodError as e:
            ctx = HTTPRequestContext(None, self.app, self.parent_context)
            # Transform it into a 405.
            exc = exc_from(e)
            exc.code = 405
            self.loop.create_task(self._safe_handle_error(ctx, exc))
        except httptools.HttpParserError as e:
            ctx = HTTPRequestContext(None, self.app, self.parent_context)
            # Transform it into a 400.
            exc = exc_from(e)
            exc.code = 400
            self.loop.create_task(self._safe_handle_error(ctx, exc))

        # Wait on the event.
        if self.waiter is None:
            self.waiter = self.loop.create_task(self._wait())
            return

    def handle_resp(self, response: Response):
        """
        Shortcut for :meth:``write_response``.
        """
        return self.write_response(response)

    def write_response(self, response: Response):
        """
        Writes a :class:`Response` to the protocol

        :param response: The response to write.
        """
        data = response.to_bytes()
        self.write(data)

    # Protocol level methods.
    def write(self, data: bytes):
        """
        Writes to the transport stream.

        This is an **internal method.** This should not be used by the developer.

        .. versionadded:: 1.9

        :param data: The data to send, byte encoded.
        """
        self._transport.write(data)

    def _empty_state(self):
        """
        Closes locks and the waiter.
        """
        # Turn off the waiter.
        if self.waiter is not None:
            self.waiter.cancel()

        self.waiter = None

        # Empty out the lock waiters by cancelling the tasks.
        for waiter in self.lock._waiters:
            waiter.cancel()

    def close(self):
        """
        Closes the transport stream.

        This an **internal method.** This should not be used by the developer.

        .. versionadded:: 1.9
        """
        # Empty the state.
        self._empty_state()

        # Then, close the transport.
        self._transport.close()
