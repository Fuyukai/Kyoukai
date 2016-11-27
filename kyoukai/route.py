"""
Routes are wrapped function objects that are called upon a HTTP request.
"""
import inspect
import typing

from werkzeug.exceptions import HTTPException
from werkzeug.wrappers import Response


class Route(object):
    """
    A route object is a wrapped function.
    They invoke this function when invoked on routing and calling.

    :ivar bp: The Blueprint this route is associated with.
    :ivar rule: The routing rule this route is associated with.
    """
    def __init__(self, function: callable):
        """
        Creates a new route object.
        :param function: The underlying callable.
            This can be a function, or any other callable.
        """
        if not callable(function):
            raise TypeError("Route arg must be callable")

        self._callable = function

        # The Blueprint this route is associated with.
        self.bp = None

        # Set on us by the Blueprint.
        self.rule = None
        self.routing_url = None

    def get_endpoint_name(self, bp):
        """
        Gets the endpoint name for this route.
        """
        if bp is not None:
            prefix = bp.name
        else:
            prefix = ""

        return prefix + ".{}".format(self._callable.__name__)

    async def invoke_function(self, ctx, *args):
        """
        Invokes the underlying callable.

        This is for use in chaining routes.
        :param ctx: The HTTPContext to use for this route.
        :param args: The arguments to pass into the route. These are automatically converted into the appropriate types.
        :return: The result of the invoked function.
        """
        # Invoke the route function.
        try:
            result = self._callable(ctx, *args)
            if inspect.isawaitable(result):
                result = await result
        except HTTPException as e:
            # This is a valid response type
            raise e
        except Exception as e:
            # Unhandled exception, so it's a 500
            raise HTTPException(500) from e
        else:
            return result

    async def invoke(self, ctx, params: typing.Container=None):
        """
        Invokes a route.

        This will run the underlying function.
        :param ctx: The HTTPContext which is used in this request.
        :param params: Any params that are used in this request.
        :return: The result of the route's function.
        """
        if params is None:
            params = {}
        # Set some useful attributes on the ctx.
        ctx.route = self

        # Invoke the route function.

        # TODO: Better argument handling.
        if isinstance(params, dict):
            p = params.values()
        else:
            if not params:
                p = ()
            else:
                p = params
        return await self.invoke_function(ctx, *p)
