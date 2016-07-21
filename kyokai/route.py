"""
Module for Kyokai routes.
"""
import re

from kyokai import blueprints
from kyokai.exc import HTTPClientException, HTTPException


class Route(object):
    """
    A route is simply a wrapped coroutine object for a request.

    It takes in a regular expression as a matcher, for the path, and a list of accepted methods.
    """

    def __init__(self, blueprint: 'blueprints.Blueprint',
                 matcher: str, methods: list, hard_match: bool=False):
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

    def __call__(self, coro):
        """
        Sets the coroutine.
        """
        self._wrapped_coro = coro
        self.__name__ = coro.__name__

    async def invoke(self, ctx):
        """
        Invoke the route, calling the underlying coroutine.
        """
        # Extract match groups.
        if not self.hard_match:
            matches = self.matcher.match(ctx.request.path).groups()
        else:
            matches = None
        # Invoke the coroutine.
        if matches:
            result = await self._wrapped_coro(ctx, *matches)
        else:
            result = await self._wrapped_coro(ctx)
        return result

    def match(self, route: str, method: str):
        """
        Short way of checkinf if the route matches.
        """
        if not self.kyokai_method_allowed(method):
            return False

        return self.kyokai_match(route)

