# Somewhere along the line, I had decided that I can't interact with others. That I have no choice but to be alone,
# but I've found a new reason to stay. It's because everyone is alone. Everyone is all alone.

# ~~~

import asyncio
import logging

from asphalt.core import Context
from kyoukai.asphalt import HTTPRequestContext
from kyoukai.blueprint import Blueprint
from werkzeug.exceptions import NotFound, MethodNotAllowed, HTTPException, InternalServerError
from werkzeug.routing import RequestRedirect
from werkzeug.wrappers import Request, Response


class Kyoukai(object):
    """
    The Kyoukai type is the main part of your web application.  It serves as the main container for your app.
    """

    def __init__(self,
                 application_name: str,
                 *,
                 server_name: str = None,
                 **kwargs):
        """
        Create the new app.

        :param application_name: The name of this application. This is currently unused.
        :param server_name: The server name. This can be None.
        """
        self.name = application_name
        self.server_name = server_name

        # Try and get the loop from the keyword arguments - don't automatically perform `get_event_loop`.
        self.loop = kwargs.get("loop")
        if not self.loop:
            self.loop = asyncio.get_event_loop()

        self.logger = logging.getLogger("Kyoukai")

        # Create the root blueprint.
        self._root_bp = Blueprint(application_name)

    @property
    def root(self) -> Blueprint:
        """
        :return: The root Blueprint for the routing tree.
        """
        return self._root_bp

    def finalize(self):
        """
        Finalizes the app and blueprints.
        """
        self.root.finalize()

    def log_route(self, request: Request, code: int):
        """
        Logs a route invocation.

        :param request: The request produced.
        :param code: The response code of the route.
        """
        fmtted = "{} {} - {}".format(request.method, request.path, code)
        self.logger.info(fmtted)

    async def handle_httpexception(self, ctx: HTTPRequestContext, exception: HTTPException,
                                   environ: dict = None) -> Response:
        """
        Handle a HTTP Exception.

        :param ctx: The context of the request.
        :param exception: The HTTPException
        :param environ: The fake WSGI environment.
        :return: A :class:`werkzeug.wrappers.Response` that handles this response.
        """
        # Try and load the error handler recursively from the ctx.route.blueprint.
        bp = ctx.bp or self.root

        error_handler = bp.get_errorhandler(exception)
        if not error_handler:
            # Try the root Blueprint. This may happen if the blueprint requested isn't registered properly in the
            # root, for some reason.
            error_handler = self.root.get_errorhandler(exception)
            if not error_handler:
                # Just return the Exception's get_response.
                return exception.get_response(environ=environ)

        else:
            # Try and invoke the error handler to get the Response.
            # Wrap it in the try/except, so we can handle a default one.
            try:
                result = await error_handler.invoke(ctx, (exception,))
            except HTTPException as e:
                # why tho?
                result = e.get_response(environ)
            except Exception as e:
                result = InternalServerError.wrap(e).get_response(environ)

            return result

    async def process_request(self, request: Request, parent_context: Context) -> Response:
        """
        Processes a Request and returns a Response object.

        This is the main processing method of Kyoukai, and is meant to be used by one of the HTTP server backends,
        and not by client code.

        :param request:
            The :class:`werkzeug.wrappers.Request` object to process.

            A new HTTPContext will be provided to wrap this request inside of to client code.

        :param parent_context:
            The :class:`asphalt.core.Context` that is the parent context for this particular app. It will be used as
            the parent for the HTTPRequestContext.

        :return: A :class:`werkzeug.wrappers.Response` object that can be written to the client as a response.
        """
        # Create a new HTTPRequestContext.
        ctx = HTTPRequestContext(parent_context, request)
        ctx.app = self

        async with ctx:
            # Call match on our Blueprint to find the request.
            try:
                matched, params = self.root.match(request.environ)
            except NotFound as e:
                # No route matched.
                self.log_route(ctx.request, 404)
                return await self.handle_httpexception(ctx, e, request.environ)
            except MethodNotAllowed as e:
                # 405 method not allowed
                self.log_route(ctx.request, 405)
                return await self.handle_httpexception(ctx, e, request.environ)
            except RequestRedirect as e:
                # slashes etc
                # user code is not allowed to handle this
                self.log_route(ctx.request, 301)
                return e.get_response(request.environ)
            else:
                ctx.route_matched.dispatch(ctx=ctx)

            ctx.route = matched
            ctx.bp = ctx.route.bp
            ctx.route_args = params

            result = None

            # Invoke the route.
            try:
                ctx.route_invoked.dispatch(ctx=ctx)
                result = await matched.invoke(ctx, params)
            except HTTPException as e:
                result = await self.handle_httpexception(ctx, e, request.environ)
            except Exception as e:
                self.logger.error("Unhandled exception in route function")
                self.logger.exception(e)
                e = InternalServerError.wrap(e)
                result = await self.handle_httpexception(ctx, e, request.environ)
            else:
                ctx.route_completed.dispatch(ctx=ctx, result=result)
            finally:
                if result:
                    # edge cases
                    self.log_route(ctx.request, result.status_code)

            # Return the new Response.
            return result
