"""
Module for Kyokai routes.
"""
import re

from asphalt.core import Context

import kyoukai
from kyoukai.context import HTTPRequestContext
from kyoukai.util import wrap_response
from kyoukai.converters import _converters, convert_args


class Route(object):
    """
    A route is simply a wrapped coroutine object for a request.

    :param blueprint: The blueprint this route is associated with.
    :param matcher: The regular expression to match routes against.
    :param methods: A :class:`list` of methods that are allowed in this route.
    :param bound: Internal. Used for views.
    :param run_hooks: If the request should run pre and post hooks, or be exempt.
    """

    def __init__(self, blueprint,
                 matcher: str, methods: list,
                 bound: bool = False,
                 run_hooks: bool = True):
        """
        Create a new Route.
        """
        self._match_str = matcher
        self._matcher = None
        self.allowed_methods = methods
        self._wrapped_coro = None

        self.bp = blueprint

        # Used for bounded routes.
        self._bound = bound

        self._view_class = None

        self.name = "<Undefined route>"

        self._should_run_hooks = run_hooks

    @property
    def matcher(self):
        """
        Gets the compiled matcher for the current route.
        :return:
        """
        if self._matcher is None:
            self._matcher = re.compile(self.bp.prefix + self._match_str)
        return self._matcher

    @property
    def self(self):
        if self._bound:
            return self._view_class
        else:
            return

    @self.setter
    def self(self, vc):
        if self._bound:
            self._view_class = vc
        else:
            raise TypeError("Attempted to update view class on unbounded route")

    def kyokai_match(self, path: str):
        """
        Check if a given path matches the specified route.
        """
        # If it's a hard match, do an lower == match
        matched = self.matcher.fullmatch(path)
        return matched

    def kyokai_method_allowed(self, meth: str):
        """
        Check if the method matches.
        """
        if meth.lower() == "head":
            return True
        meths = [m.lower() for m in self.allowed_methods]
        if 'any' in meths:
            return True
        in_m = meth.lower() in meths
        return in_m

    def create(self, coro):
        """
        Set the internal coroutine state from the passed in value.
        """
        self._wrapped_coro = coro
        self.name = coro.__name__
        return self

    def __repr__(self):
        return "<Route '{}' in blueprint {}>".format(self.name, repr(self.bp))

    def __call__(self, coro):
        """
        Sets the coroutine.
        """
        return self.create(coro)

    async def invoke(self, ctx: HTTPRequestContext, exception=None):
        """
        Invoke the route, calling the underlying coroutine.
        """
        if self._should_run_hooks:
            # Run pre-request hooks.
            hooks = self.bp.get_pre_hooks(ctx)
            if hooks:
                for hook in hooks:
                    # Await the hook.
                    ctx = await hook(ctx)
                    if not isinstance(ctx, Context):
                        # idc about the subtype, as long as it's a context.
                        raise TypeError("Hook {} returned non-context".format(hook.__name__))

        m_obj = self.matcher.fullmatch(ctx.request.path)
        if m_obj:
            matches = m_obj.groups()
        else:
            matches = []

        # Invoke the coroutine.
        # Construct the params.
        params = []
        if self._bound:
            params.append(self.self)

        params.append(ctx)

        if exception:
            # This is an error handler, so add the exception.
            params.append(exception)

        if matches:
            params += list(matches)

        # Convert the arguments.
        args = await convert_args(ctx, self._wrapped_coro, *params, bound=self._bound)

        result = await self._wrapped_coro(*args)
        # Wrap the result.
        result = wrap_response(result, response_cls=ctx.app.response_cls)

        if self._should_run_hooks:
            hooks = self.bp.get_post_hooks(ctx)
            if hooks:
                for hook in hooks:
                    result = await hook(ctx, result)
                    if not isinstance(result, kyoukai.Response):
                        raise TypeError("Hook {} returned non-response".format(hook.__name__))
                    result = wrap_response(result)

        # Set the request object.
        result.request = ctx.request

        return result

    def match(self, route: str, method: str):
        """
        Short way of checking if the route matches.

        This does *not* check if the method matches.
        """
        matched = self.kyokai_match(route)
        if matched:
            return self
