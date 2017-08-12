"""
A high-performance HTTP/1.1 backend for the Kyoukai webserver using `httptools 
<https://github.com/MagicStack/httptools>`_.
"""
import asyncio
import base64
import gzip
import logging
import traceback
import warnings
import zlib
from io import BytesIO

import httptools
from asphalt.core import Context
from werkzeug.exceptions import MethodNotAllowed, BadRequest, InternalServerError
from werkzeug.wrappers import Response

from kyoukai.backends.http2 import H2KyoukaiProtocol
from kyoukai.wsgi import to_wsgi_environment, get_formatted_response

CRITICAL_ERROR_TEXT = """HTTP/1.0 500 INTERNAL SERVER ERROR
Server: Kyoukai
X-Powered-By: Kyoukai
X-HTTP-Backend: httptools
Content-Type: text/html; charset=utf-8
Content-Length: 310

<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">
<title>Critical Server Error</title>
<h1>Critical Server Error</h1>
<p>An unrecoverable error has occurred within Kyoukai.
If you are the developer, please report this at <a href="https://github.com/SunDwarf/Kyoukai">the 
Kyoukai issue tracker.</a>
""".replace("\n", "\r\n")

HTTP_SWITCHING_PROTOCOLS = """HTTP/1.1 101 SWITCHING PROTOCOLS
Connection: Upgrade
Upgrade: h2c
Server: Kyoukai
X-Powered-By: Kyoukai
X-HTTP-Backend: httptools
Content-Length: 0

""".replace("\n", "\r\n")

HTTP_TOO_BIG = """HTTP/1.1 413 PAYLOAD TOO LARGE
Server: Kyoukai
X-Powered-By: Kyoukai
X-HTTP-Backend: httptools
Content-Length: 0

""".replace("\n", "\r\n")

HTTP_INVALID_COMPRESSION = """HTTP/1.1 400 BAD REQUEST
Server: Kyoukai
X-Powered-By: Kyoukai
X-HTTP-Backend: httptools
Content-Length: 25

Invalid compressed data
""".replace("\n", "\r\n")

PROTOCOL_CLASS = "KyoukaiProtocol"


class KyoukaiProtocol(asyncio.Protocol):  # pragma: no cover
    """
    The base protocol for Kyoukai using httptools for a HTTP/1.0 or HTTP/1.1 interface.
    """
    MAX_BODY_SIZE = 12 * 1024 * 1024

    def __init__(self, component, parent_context: Context,
                 server_ip: str, server_port: int):
        """
        :param component: The :class:`kyoukai.asphalt.KyoukaiComponent` associated with this request.
        :param parent_context: The parent context for this request.
            A new HTTPRequestContext will be derived from this.
        """

        self.component = component
        self.app = component.app
        self.parent_context = parent_context

        self.server_ip = server_ip
        self.server_port = server_port

        # Transport.
        # This is written to by our request when it's done.
        self.transport = None  # type: asyncio.WriteTransport

        # Request lock.
        # This ensures that requests are processed serially, and responded to in the correct order,
        # as the lock is released after processing a request completely.
        self.lock = asyncio.Lock()

        # The parser itself.
        # This is created per connection, and uses our own class.
        self.parser = httptools.HttpRequestParser(self)

        # A waiter that 'waits' on the event to clear.
        # Once the wait is over, it then delegates the request to the app.
        self.waiter = None  # type: asyncio.Task

        # The IP and port of the client.
        self.ip, self.client_port = None, None

        # Intermediary data storage.
        # This is a list because headers are appended as (Name, Value) pairs.
        # In HTTP/1.1, there can be multiple headers with the same name but different values.
        self.headers = []
        self.body = BytesIO()
        self.full_url = ""

        self.loop = self.app.loop
        self.logger = logging.getLogger("Kyoukai.HTTP11")

    def replace(self, other: type, *args, **kwargs) -> type:
        """
        Replaces our type with the other.
        """
        # Copy the properties we need.
        component = self.component
        app = component.app
        # Goodbye, ourselves!
        self.__class__ = other

        # Hello, not ourselves!
        # Call the new __init__.
        other.__init__(self, component, app, *args, **kwargs)

        return self

    # httptools callbacks
    def on_message_begin(self):
        """
        Called when a message begins.
        """
        self.body = BytesIO()
        self.headers = []
        self.full_url = ""

    def on_header(self, name: bytes, value: bytes):
        """
        Called when a header has been received.

        :param name: The name of the header.
        :param value: The value of the header.
        """
        self.headers.append((name.decode(), value.decode()))

    def on_headers_complete(self):
        """
        Called when the headers have been completely sent.
        """

    def on_body(self, body: bytes):
        """
        Called when part of the body has been received.

        :param body: The body text.
        """
        self.body.write(body)
        if self.body.tell() >= self.MAX_BODY_SIZE:
            # write a "too big" message
            self.write(HTTP_TOO_BIG)
            self.close()

    def on_url(self, url: bytes):
        """
        Called when a URL is received from the client.
        """
        self.full_url = url.decode("utf-8")

    def on_message_complete(self):
        """
        Called when a message is complete.
        This creates the worker task which will begin processing the request.
        """
        task = self.loop.create_task(self._wait_wrapper())
        self.waiter = task

    # asyncio procs
    def connection_made(self, transport: asyncio.WriteTransport):
        """
        Called when a connection is made via asyncio.

        :param transport: The transport this is using.
        """
        try:
            self.ip, self.client_port = transport.get_extra_info("peername")
            self.logger.debug("Connection received from {}:{}".format(self.ip, self.client_port))
        except ValueError:
            # Sometimes socket.socket.getpeername() isn't available, so it tried to unpack a None.
            # Or, it returns None (wtf?)
            # So just provide some fake values.
            warnings.warn("getpeername() returned None, cannot provide transport information.")
            self.ip, self.client_port = None, None

        self.transport = transport

        ssl_sock = self.transport.get_extra_info("ssl_object")
        if ssl_sock is not None:
            # Check if we negotiated a HTTP/2 connection.
            # This will check the ALPN protocol, but failing that, fall back to the NPN protocol.
            negotiated_protocol = ssl_sock.selected_alpn_protocol()
            if negotiated_protocol is None:
                negotiated_protocol = ssl_sock.selected_npn_protocol()

            if negotiated_protocol == "h2":
                # switch protocol to http/2 handler
                transport = self.transport
                new_self = self.replace(H2KyoukaiProtocol)  # type: H2KyoukaiProtocol
                # make sure the new connection
                type(new_self).connection_made(new_self, transport)
                return

        self.component.connection_made.dispatch(protocol=self)

    def connection_lost(self, exc):
        self.logger.debug("Connection lost from {}:{}".format(self.ip, self.client_port))
        self.component.connection_lost.dispatch(protocol=self)

    def data_received(self, data: bytes):
        """
        Called when data is received into the connection.
        """
        # Feed it into the parser, and handle any errors that might happen.
        try:
            self.parser.feed_data(data)
        except httptools.HttpParserInvalidMethodError as e:
            # Exceptions here are a bit tricky.
            # We can't simply call into the app to have it handle a 405/400 - there's no Request,
            # or environment. Instead, what we do is call a wrapper function
            # (handle_parser_exception) which will generate a fake WSGI environment, and then
            # automatically return a werkzeug httpexception that corresponds.
            self.handle_parser_exception(e)
        except httptools.HttpParserError as e:
            traceback.print_exc()
            self.handle_parser_exception(e)
        except httptools.HttpParserUpgrade as e:
            # It's a HTTP upgrade!
            # The only valid values of these that we wish to support (currently) are `h2c` and
            # `Websocket`. Currently, Kyoukai does not support websocket upgrade (soon™).
            # However, we cannot silently ignore websocket upgrades - we discard those for now and
            # disconnect.
            # Anything else, we also discard and disconnect.

            # httptools sucks, and only provides us an offset.
            # so what we do is hope the `Upgrade` header is in our header list.
            for name, header in self.headers:
                if name.lower() == "upgrade":
                    upgrade = header
                    break
            else:
                # thanks, we can't do shit.
                self.handle_parser_exception(e)
                return
            # If it's h2c, replace ourselves with the HTTP/2 client.
            if upgrade.lower() == "h2c":
                # Copy the transport into our local scope, as it becomes None after we've switched
                # type. Once we've replaced ourselves, call `connection_made` on the new type to
                # initialize.
                for name, header in self.headers:
                    if name.lower() == "http2-settings":
                        http2_settings = header
                        break
                else:
                    # can't find the http2_settings header, rip
                    self.handle_parser_exception(e)
                    return

                self.logger.info("Upgrading HTTP/1.1 to HTTP/2 connection.")

                # base64 decode the http2 settings packet
                decoded = base64.urlsafe_b64decode(http2_settings)
                # send a 101 switching protocols
                self.write(HTTP_SWITCHING_PROTOCOLS)

                transport = self.transport
                new_self = self.replace(H2KyoukaiProtocol)  # type: H2KyoukaiProtocol

                # update with the new settings
                new_self.conn.initiate_upgrade_connection(decoded)
                # this will have updated settings; now switch protocols.
                type(new_self).connection_made(new_self, transport)
                return

            # If it's Websocket, disconnect.
            if upgrade.lower() == "websocket":
                self.handle_parser_exception(e)
                return

            # If it's anything else, disconnect.
            self.handle_parser_exception(e)
            return

    # kyoukai handling
    def handle_parser_exception(self, exc: Exception):
        """
        Handles an exception when parsing.

        This will not call into the app (hence why it is a normal function, and not a coroutine).
        It will also close the connection when it's done.

        :param exc: The exception to handle.
        """
        if isinstance(exc, httptools.HttpParserInvalidMethodError):
            # 405 method not allowed
            r = MethodNotAllowed()
        elif isinstance(exc, httptools.HttpParserError):
            # 400 bad request
            r = BadRequest()
        elif isinstance(exc, httptools.HttpParserUpgrade):
            r = BadRequest(description="Invalid upgrade header.")
        else:
            # internal server error
            r = InternalServerError()

        # Make a fake environment.
        new_environ = to_wsgi_environment(headers=self.headers, method="", path="/",
                                          http_version="1.0", body=None)
        new_environ["SERVER_NAME"] = self.component.get_server_name()
        new_environ["SERVER_PORT"] = str(self.server_port)
        new_environ["REMOTE_ADDR"] = self.ip

        self.raw_write(get_formatted_response(r, new_environ))
        self.parser = httptools.HttpRequestParser(self)
        self.close()

    async def _wait_wrapper(self):
        try:
            if hasattr(self, "_wait"):
                await self._wait()
            else:
                return
        except:
            self.logger.critical("Error in Kyoukai's HTTP handling!", exc_info=True)
            self._raw_write(CRITICAL_ERROR_TEXT.encode())
            self.close()
        finally:
            # we might have change protocol by now.
            # if so, don't try and cancel the non-existant thing.
            if hasattr(self, "waiter"):
                self.waiter.cancel()
                self.waiter = None
                self.parser = httptools.HttpRequestParser(self)

    async def _wait(self):
        """
        The main core of the protocol.

        This constructs a new Werkzeug request from the headers.
        """
        # Check if the body has data in it by asking it to tell us what position it's seeked to.
        # If it's > 0, it has data, so we can use it. Otherwise, it doesn't, so it's useless.
        told = self.body.tell()
        if told:
            self.logger.debug("Read {} bytes of body data from the connection".format(told))
            self.body.seek(0)
            body = self.body
        else:
            body = None

        version = self.parser.get_http_version()
        method = self.parser.get_method().decode()

        for header, value in self.headers:
            # check if a content-encoding has been passed
            if header == "Content-Encoding" and body is not None:
                # no special encoding
                if value == "identity":
                    pass

                # gzip, decompress as such
                elif value == "gzip":
                    self.logger.debug("Decoding body data as gzip.")
                    try:
                        decompressed_data = gzip.decompress(body.read())
                    except zlib.error:
                        self.write(HTTP_INVALID_COMPRESSION)
                        self.close()
                        return

                    body = BytesIO(decompressed_data)

                # deflate, decompress as such
                elif value == "deflate":
                    z = zlib.decompressobj(6, zlib.DEFLATED, -zlib.MAX_WBITS, zlib.DEF_MEM_LEVEL, 0)
                    try:
                        decompressed_data = z.decompress(body.read())
                    except zlib.error:
                        self.write(HTTP_INVALID_COMPRESSION)
                        self.close()
                        return

                    body = BytesIO(decompressed_data)
                else:
                    self.logger.error("Unknown Content-Encoding sent by client: {}".format(value))

        new_environ = to_wsgi_environment(headers=self.headers, method=method, path=self.full_url,
                                          http_version=version, body=body)

        new_environ["kyoukai.protocol"] = self
        new_environ["SERVER_NAME"] = self.component.get_server_name()
        new_environ["SERVER_PORT"] = str(self.server_port)
        new_environ["REMOTE_ADDR"] = self.ip
        new_environ["REMOTE_PORT"] = self.client_port

        # Construct a Request object.
        new_r = self.app.request_class(new_environ, False)

        # Invoke the app.
        async with self.lock:
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
