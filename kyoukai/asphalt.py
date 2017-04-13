"""
Asphalt wrappers for Kyoukai.
"""
import abc
import importlib
import logging
import socket
import ssl as py_ssl
from functools import partial

from asphalt.core import resolve_reference, Context
from asphalt.core.component import Component
from asphalt.core.event import Signal, Event
from werkzeug.routing import Rule
from werkzeug.wrappers import Request, Response

from kyoukai.blueprint import Blueprint
from kyoukai.route import Route


# Asphalt events.
class ConnectionMadeEvent(Event):  # pragma: no cover
    """
    Dispatched when a connection is made to the server.

    This does NOT fire when using WSGI workers.

    This has the protocol as the ``protocol`` attribute.
    """

    def __init__(self, source, topic, *, protocol):
        super().__init__(source, topic)
        self.protocol = protocol


class ConnectionLostEvent(ConnectionMadeEvent):  # pragma: no cover
    """
    Dispatched when a connection is lost from the server.

    This does NOT fire when using WSGI workers.

    This has the protocol as the ``protocol`` attribute.
    """


class CtxEvent(Event):  # pragma: no cover
    def __init__(self, source, topic, *, ctx: 'HTTPRequestContext'):
        super().__init__(source, topic)
        self.ctx = ctx


class RouteMatchedEvent(CtxEvent):  # pragma: no cover
    """
    Dispatched when a route is matched.

    This has the context as the ``ctx`` attribute, and the route can be accessed via ``ctx.route``.
    """


class RouteInvokedEvent(CtxEvent):  # pragma: no cover
    """
    Dispatched when a route is invoked.

    This has the context as the ``ctx`` attribute.
    """


class RouteReturnedEvent(CtxEvent):  # pragma: no cover
    """
    Dispatched after a route has returned.

    This has the context as the ``ctx`` attribute and the response as the ``result`` attribute.
    """

    def __init__(self, source, topic, *, ctx, result: Response):
        super().__init__(source, topic, ctx=ctx)
        self.result = result


class KyoukaiBaseComponent(Component, metaclass=abc.ABCMeta):  # pragma: no cover
    """
    The base class for any component used by Kyoukai.

    This one does not create a Server instance; it should be used when you are using a different 
    HTTP server backend.
    """
    connection_made = Signal(ConnectionMadeEvent)
    connection_lost = Signal(ConnectionLostEvent)

    def __init__(self, app, ip: str = "127.0.0.1", port: int = 4444, **cfg):
        from kyoukai.app import Kyoukai
        if not isinstance(app, Kyoukai):
            app = resolve_reference(app)

        #: The application object for a this component.
        self.app = app

        #: The IP address to boot the server on.
        self.ip = ip

        #: The port to boot the server on.
        self.port = port

        #: The config file to use.
        self.cfg = cfg

        #: The :class:`asyncio.Server` instance that is serving us today.
        self.server = None

        #: The base context for this server.
        self.base_context = None  # type: Context

        #: The backend to use for the HTTP server.
        self.backend = self.cfg.get("backend", "kyoukai.backends.httptools_")

        self.logger = logging.getLogger("Kyoukai")

        self._server_name = app.server_name or socket.getfqdn()

    @abc.abstractmethod
    async def start(self, ctx: Context):
        """
        Overridden in subclasses to spawn a new server.
        """

    def get_server_name(self):
        """
        :return: The server name of this app.
        """
        return self.app.server_name or self._server_name

    def get_protocol(self, ctx: Context, serv_info: tuple):
        """
        Gets the protocol to use for this webserver.
        """
        if not hasattr(self, "_cached_mod"):
            mod = importlib.import_module(self.backend)
            self._cached_mod = mod

        server = getattr(self._cached_mod, self._cached_mod.PROTOCOL_CLASS)
        proto = server(self, ctx, *serv_info)
        ctx.protocol = proto
        return proto


class KyoukaiComponent(KyoukaiBaseComponent):  # pragma: no cover
    """
    A component for Kyoukai.
    This includes the built-in HTTP server.  
    
    .. versionchanged:: 2.2
    
        Passing ``run_server`` as False will not run the inbuilt web server.
    """
    connection_made = Signal(ConnectionMadeEvent)
    connection_lost = Signal(ConnectionLostEvent)

    def __init__(self, app, ip: str = "127.0.0.1", port: int = 4444,
                 **cfg):
        """
        Creates a new component.

        :param app: The application object to use.
            This can either be the real application object, or a string that resolves to a \
            reference for the real application object.

        :param ip: If using the built-in HTTP server, the IP to bind to.
        :param port: If using the built-in HTTP server, the port to bind to.
        :param cfg: Additional configuration.
        """
        super().__init__(app, ip, port, **cfg)

        self.app.config.update(self.cfg)

        for key, value in cfg.items():
            setattr(self, key, value)

    def get_server_name(self):
        """
        :return: The server name of this app.
        """
        return self.app.server_name or self._server_name

    async def start(self, ctx: Context):
        """
        Starts the webserver if required.

        :param ctx: The base context.
        """
        self.base_context = ctx

        ssl_context = None

        if self.cfg.get("ssl", {}):
            ssl = self.cfg["ssl"]
            if ssl.get("enabled") is True:
                ssl_context = py_ssl.create_default_context(py_ssl.Purpose.CLIENT_AUTH)
                # override the ciphers
                ssl_context.set_ciphers(
                    "ECDH+CHACHA20:ECDH+CHACHA20:"         # CHACHA20 for newer openssl
                    "ECDH+AES128:RSA+AES128:"              # Standard AES
                    "ECDH+AES256:RSA+AES256:"              # Slower AES
                    "ECDH+3DES:RSA+3DES:"                  # 3DES for older systems
                    "!aNULL:!eNULL:!MD5:!DSS:!RC4")        # Disable insecure ciphers
                ssl_context.load_cert_chain(certfile=ssl["ssl_certfile"],
                                            keyfile=ssl["ssl_keyfile"])

                if self.cfg.get("http2", False) is True:
                    ssl_context.set_alpn_protocols(["h2"])

                    try:
                        ssl_context.set_npn_protocols(["h2"])
                    except NotImplementedError:
                        # NPN protocol doesn't work here, so don't bother setting it
                        pass

                self.logger.info("Using HTTP over TLS.")

        if self.cfg.get("run_server", True) is True:
            protocol = partial(self.get_protocol, ctx, (self._server_name, self.port))
            self.app.finalize()
            self.server = await self.app.loop.create_server(protocol, self.ip, self.port,
                                                            ssl=ssl_context)
            self.logger.info("Kyoukai serving on {}:{}.".format(self.ip, self.port))


class HTTPRequestContext(Context):
    """
    The context subclass passed to all requests within Kyoukai.
    """
    route_matched = Signal(RouteMatchedEvent)
    route_invoked = Signal(RouteInvokedEvent)
    route_completed = Signal(RouteReturnedEvent)

    def __init__(self, parent: Context, request: Request):
        super().__init__(parent)

        #: The :class:`~.Kyoukai` object this request is handling.
        self.app = None  # type: Kyoukai

        #: The :class:`werkzeug.wrappers.Request` object this request is handling.
        self.request = request

        #: The :class:`~.Route` object this request is for.
        self.route = None  # type: Route

        #: The :class:`~.Blueprint` object this request is for.
        self.bp = None  # type: Blueprint

        #: The :class:`werkzeug.routing.Rule` object associated with this request.
        self.rule = None  # type: Rule

        #: The WSGI environment for this request.
        self.environ = self.request.environ  # type: dict

        #: The :class:`asyncio.Protocol` protocol handling this connection.
        self.proto = None

    def url_for(self, endpoint: str, *, method: str = None, **kwargs):
        """
        A context-local version of ``url_for``.

        For more information, see the documentation on :meth:`~.Blueprint.url_for`.
        """
        return self.app.url_for(self.environ, endpoint, method=method, **kwargs)
