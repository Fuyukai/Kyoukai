# Somewhere along the line, I had decided that I can't interact with others. That I have no choice but to be alone,
# but I've found a new reason to stay. It's because everyone is alone. Everyone is all alone.

# ~~~

import asyncio
import logging

import werkzeug
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
                 server_name: str=None,
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

        async with ctx:
            # Call match on our Blueprint to find the request.
            # TODO: ERROR HANDLING
            try:
                matched, params = self.root.match(request.environ)
            except NotFound as e:
                # No route matched.
                return e.get_response(request.environ)
            except MethodNotAllowed as e:
                # 405 method not allowed
                return e.get_response(request.environ)
            except RequestRedirect as e:
                # slashes etc
                return e.get_response(request.environ)

            # Invoke the route.
            try:
                result = await matched.invoke(ctx, params)
            except HTTPException as e:
                return e.get_response(request.environ)
            except Exception as e:
                self.logger.error("Unhandled exception in route function")
                self.logger.exception(e)
                return InternalServerError().get_response(request.environ)

            # Return the new Response.
            return result
