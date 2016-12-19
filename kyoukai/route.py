"""
Routes are wrapped function objects that are called upon a HTTP request.
"""
import inspect
import typing

from werkzeug.exceptions import HTTPException
from werkzeug.routing import Rule
from werkzeug.wrappers import Response


class Route(object):
    """
    A route object is a wrapped function.
    They invoke this function when invoked on routing and calling.

    :ivar bp: The Blueprint this route is associated with.
    :ivar rule: The routing rule this route is associated with.
    """
    def __init__(self, function: callable, reverse_hooks: bool=False,
                 should_invoke_hooks: bool=True):
        """
        Creates a new route object.
        :param function: The underlying callable.
            This can be a function, or any other callable.

        :param reverse_hooks: If the request hooks should be reversed for this request (i.e child to parent.)
        :param should_invoke_hooks: If request hooks should be invoked.
            This is automatically False for error handlers.
        """
        if not callable(function):
            raise TypeError("Route arg must be callable")

        self._callable = function

        # The Blueprint this route is associated with.
        self.bp = None  # type: Blueprint

        # Set on us by the Blueprint.
        self.rule = None  # type: Rule
        self.routing_url = None

        self.methods = []

        self.reverse_hooks = reverse_hooks

        self.should_invoke_hooks = should_invoke_hooks

    def create_rule(self) -> Rule:
        """
        Creates the rule object used by this route.

        :return: A new :class:`Rule` that is to be used for this route.
        """
        return Rule(self.bp.prefix + self.routing_url, methods=self.methods, endpoint=self.get_endpoint_name(self.bp))

    def get_endpoint_name(self, bp=None):
        """
        Gets the endpoint name for this route.
        """
        if bp is not None:
            prefix = bp.name
        else:
            prefix = self.bp.name if self.bp else ""

        return prefix + ".{}".format(self._callable.__name__)

    async def invoke_function(self, ctx, pre_hooks: list, post_hooks: list, **kwargs):
        """
        Invokes the underlying callable.

        This is for use in chaining routes.
        :param ctx: The HTTPContext to use for this route.
        :return: The result of the invoked function.
        """
        # Invoke the route function.
        try:
            # Invoke pre-request hooks, setting `ctx` equal to the new value.
            if self.should_invoke_hooks:
                for hook in pre_hooks:
                    ctx = await hook(ctx)

            result = self._callable(ctx, **kwargs)
            if inspect.isawaitable(result):
                result = await result
        except HTTPException as e:
            # This is a valid response type
            raise e
        except Exception as e:
            # Unhandled exception, so it's a 500
            raise HTTPException(500) from e
        else:
            # Invoke post-request hooks. These happen inside this `else` block because post-request hooks are only meant
            # to happen if the route invoked successfully.
            if self.should_invoke_hooks:
                for hook in post_hooks:
                    result = await hook(ctx, result)

            return result

    def check_route_args(self, params: dict=None):
        """
        Checks the arguments for a route.

        :param params: The parameters passed in, as a dict.
        :raises TypeError: If the arguments passed in were not correct.
        """
        # Get the signature of our callable.
        sig = inspect.signature(self._callable, follow_wrapped=True)  # type: inspect.Signature
        f_nargs = len(sig.parameters) - 1
        # If the lengths of the signature and the params are different, it's obviously wrong.
        if f_nargs != len(params):  # + 1 because `ctx` is a param
            raise TypeError("Route takes {} args, passed in {} instead".format(f_nargs, len(params)))

        # Next, check that all the argument names in the signature are in the params, so that they can be easily double
        # star expanded into the function.
        for n, (name, arg) in enumerate(sig.parameters.items()):
            # Skip the first argument, because it is usually the HTTPRequestContext, and we don't want to type check
            # that.
            if n == 0:
                continue
            assert isinstance(arg, inspect.Parameter)
            if arg.name not in params:
                raise ValueError("Argument {} not found in args for callable {}".format(arg.name,
                                                                                        self._callable.__name__))

            # Also, check that the type of the arg and the annotation matches.
            value = params[arg.name]
            if arg.annotation is None:
                # No annotation, don't type check
                continue

            if not isinstance(value, arg.annotation):
                raise TypeError("Argument {} must be type {} (got type {})".format(
                    arg.name, arg.annotation, type(value))
                )

    async def invoke(self, ctx, params: typing.Container=None) -> Response:
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
        if not params:
            params = {}

        self.check_route_args(params)

        # Try and get the hooks.
        pre_hooks = self.bp.get_hooks("pre")
        if self.reverse_hooks:
            pre_hooks = reversed(pre_hooks)

        post_hooks = self.bp.get_hooks("post")
        if self.reverse_hooks:
            post_hooks = reversed(post_hooks)
        return await self.invoke_function(ctx, pre_hooks, post_hooks, **params)
