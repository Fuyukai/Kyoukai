"""
A regex-based routing engine for Kyoukai.

This uses regular expressions to match the route objects.
"""
import re
import sre_constants
import typing

from asphalt.core import Context
from kyoukai.context import HTTPRequestContext
from kyoukai.response import Response
from kyoukai.converters import convert_args
from kyoukai.exc import HTTPException
from kyoukai.routing.base import ABCRouter, ABCRoute
from kyoukai.util import wrap_response


class RegexRoute(ABCRoute):
    """
    Defines a regular expression based route.
    """

    def __init__(self, blueprint,
                 matcher: str, methods: list,
                 bound: bool = False,
                 run_hooks: bool = True):

        super().__init__(blueprint, matcher, methods, bound, run_hooks)

        self._matcher = None

    def __repr__(self):
        return "<RegexRoute '{}'>".format(self.bp.prefix + self._match_str)

    @property
    def matcher(self):
        """
        This is used by the RegexRouter.

        :return: A compiled regular expression for this route.
        """
        if self._matcher is None:
            try:
                self._matcher = re.compile(self.bp.prefix + self._match_str)
            except sre_constants.error as e:
                # Raise a new HTTPException(500) from this.
                exc = HTTPException(500)
                exc.route = self
                raise exc from e
        return self._matcher

    async def invoke(self, ctx: HTTPRequestContext, args: typing.Iterable = None, exception: Exception = None):
        if self._should_run_hooks:
            # Run pre-request hooks.
            hooks = self.bp.gather_hooks("pre")
            if hooks:
                for hook in hooks:
                    # Await the hook.
                    ctx = await hook(ctx)
                    if not isinstance(ctx, Context):
                        # idc about the subtype, as long as it's a context.
                        raise TypeError("Hook {} returned non-context".format(hook.__name__))

        # Invoke the coroutine.
        # Construct the params.
        params = []
        if self._bound:
            params.append(self.self)

        params.append(ctx)

        if exception:
            # This is an error handler, so add the exception.
            params.append(exception)

        # Add args to params.
        if args:
            params += list(args)

        # Convert the arguments.
        if self.should_convert:
            args = await convert_args(ctx, self._wrapped_coro, *params, bound=self._bound)
        else:
            # Don't bother with converting.
            args = params

        # Call the coroutine.

        result = await self._wrapped_coro(*args)
        # Wrap the result.
        result = wrap_response(result, response_cls=ctx.app.response_cls)

        if self._should_run_hooks:
            hooks = self.bp.get_post_hooks(ctx)
            if hooks:
                for hook in hooks:
                    result = await hook(ctx, result)
                    if not isinstance(result, Response):
                        raise TypeError("Hook {} returned non-response".format(hook.__name__))
                    result = wrap_response(result)

        # Set the request object.
        result.request = ctx.request

        return result


class RegexRouter(ABCRouter):
    """
    A regex-based router.
    """

    def match(self, path: str, method: str):
        """
        Matches the routes via the regexes.
        """
        root_bp = self.app.root
        # Gather all routes, and iterate through them.
        routes = root_bp.gather_routes()

        matched = []
        for route in routes:
            assert isinstance(route, RegexRoute), "Routes must be instances of RegexRoute"
            # If the matcher works, add it to matched.
            m_obj = route.matcher.fullmatch(path)
            if m_obj:
                matched.append((route, m_obj.groups()))

        # If none matched, then return None.
        if not matched:
            return None

        # Loop over all the Blueprints that matched, and check if any have a matching method.
        for match in matched:
            if match[0].method_allowed(method):
                return match

        else:
            # Extract the blueprints (the first item)
            bps = (_[0] for _ in matched)

            # Calculate the 405 blueprint.
            fof_bp = self.calculate_405_errorhandler(bps)

            exc = HTTPException(405)
            exc.bp = fof_bp
            raise fof_bp
