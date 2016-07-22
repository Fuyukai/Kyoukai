"""
Module for Kyokai routes.
"""
import re

from asphalt.core import Context

import kyokai
from kyokai.context import HTTPRequestContext
from kyokai.exc import HTTPClientException, HTTPException


class Route(object):
    """
    A route is simply a wrapped coroutine object for a request.

    It takes in a regular expression as a matcher, for the path, and a list of accepted methods.
    """

    def __init__(self, blueprint: 'blueprints.Blueprint',
                 matcher: str, methods: list, hard_match: bool = False,
                 bound: bool = False):
        """
        Create a new Route.
        """
        if hard_match:
            self.matcher = matcher
        else:
            self.matcher = re.compile(matcher)
        self.allowed_methods = methods
        self.hard_match = hard_match
        self._wrapped_coro = None

        self.bp = blueprint

        # Used for bounded routes.
        self._bound = bound

        self._view_class = None

        self.name = "<Undefined route>"

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
        if self.hard_match:
            matched = path.lower() == self.matcher.lower()
        else:
            matched = self.matcher.match(path)
        return matched

    def kyokai_method_allowed(self, meth: str):
        """
        Check if the method matches.
        """
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
        return "<Route `{}` in blueprint `{}`>".format(self.name, repr(self.bp))

    def __call__(self, coro):
        """
        Sets the coroutine.
        """
        return self.create(coro)

    async def invoke(self, app, ctx: HTTPRequestContext):
        """
        Invoke the route, calling the underlying coroutine.
        """
        # Run pre-request hooks.
        hooks = self.bp.get_pre_hooks(ctx)
        if hooks:
            for hook in hooks:
                # Await the hook.
                ctx = await hook(ctx)
                if not isinstance(ctx, Context):
                    # idc about the subtype, as long as it's a context.
                    raise TypeError("Hook {} returned non-context".format(hook.__name__))

        # Extract match groups.
        if not self.hard_match:
            matches = self.matcher.match(ctx.request.path).groups()
        else:
            matches = None
        # Invoke the coroutine.
        # Construct the params.
        params = []
        if self._bound:
            params.append(self.self)

        params.append(ctx)

        if matches:
            params += list(matches)

        result = await self._wrapped_coro(*params)
        # Wrap the result.
        result = app._wrap_response(result)

        hooks = self.bp.get_post_hooks(ctx)
        if hooks:
            for hook in hooks:
                result = await hook(ctx, result)
                if not isinstance(result, kyokai.Response):
                    raise TypeError("Hook {} returned non-response".format(hook.__name__))
                result = app._wrap_response(result)

        return result

    def match(self, route: str, method: str):
        """
        Short way of checkinf if the route matches.
        """
        matched = self.kyokai_match(route)
        if matched:
            if not self.kyokai_method_allowed(method):
                # Raise a HTTPException.
                raise HTTPException(405, route=self)

        return self.kyokai_match(route)
