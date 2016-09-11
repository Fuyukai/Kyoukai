"""
A regex-based routing engine for Kyoukai.

This uses regular expressions to match the route objects.
"""
import re
import sre_constants

from kyoukai.exc import HTTPException
from kyoukai.routing.base import ABCRouter, ABCRoute


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
            m_obj = route.matcher.fullmatch(route)
            if m_obj:
                matched.append((route, m_obj.groups()))

        # If none matched, then raise a 404.
        if not matched:
            raise HTTPException(404)

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
