"""
Module for Kyokai routes.
"""
import re

from kyokai.exc import HTTPClientException, HTTPException


class Route(object):
    """
    A route is simply a wrapped coroutine object for a request.

    It takes in a regular expression as a matcher, for the path, and a list of accepted methods.
    """

    def __init__(self, matcher: str, methods: list):
        """
        Create a new Route.
        """
        self.matcher = re.compile(matcher)
        self.allowed_methods = methods
        self._wrapped_coro = None

    def kyokai_match(self, path: str, method: str):
        """
        Check if a given path matches the specified route.
        """
        matched = self.matcher.match(path)
        in_m = method.lower() in [m.lower() for m in self.allowed_methods]
        return (matched and in_m)

    def __call__(self, coro):
        """
        Sets the coroutine.
        """
        self._wrapped_coro = coro

    async def invoke(self, request):
        """
        Invoke the route, calling the underlying coroutine.
        """
        # Extract match groups.
        matches = self.matcher.match(request.path).groups()
        # Invoke the coroutine.
        try:
            if matches:
                result = await self._wrapped_coro(request, *matches)
            else:
                result = await self._wrapped_coro(request)
        except Exception as e:
            if isinstance(e, HTTPClientException):
                raise
            else:
                raise HTTPException(500)
        return result

