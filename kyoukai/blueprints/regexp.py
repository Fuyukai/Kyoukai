"""
Regular-expression based blueprint for Kyoukai.

This produces regex-based routes when ``wrap_route`` is called, and is the default blueprint handler for the Kyoukai
blueprint tree.
"""
import typing

from kyoukai.blueprints.base import ABCBlueprint
from kyoukai.routing.base import ABCRoute
from kyoukai.routing.regexp import RegexRoute


class RegexBlueprint(ABCBlueprint):
    """
    The class for a RegexBlueprint.

    RegexBlueprints are very simple compared to other types of blueprints, using a basic regular expression to match
    the path of of a request with a route. This means there is no complex type conversion, as there is with
    :class:`kyoukai.blueprints.wz.WerkzeugBlueprint`, and the routes used can be incredibly powerful.
    """

    def __init__(self, name: str, parent: 'ABCBlueprint' = None,
                 url_prefix: str = ""):
        super().__init__(name, parent, url_prefix)

        # Define the routes list.
        self.routes = []

    def add_route(self, route: 'ABCRoute'):
        # Adds the route to self.route
        self.routes.append(route)
        return route

    def wrap_route(self, match_string: str, coroutine: typing.Awaitable, *, methods: list = None,
                   run_hooks = True) -> ABCRoute:
        # Wrap the route in an RegexRoute instance.
        rtt = RegexRoute(self, match_string, methods, bound=False, run_hooks=run_hooks)
        rtt.create(coroutine)

        return rtt

    def gather_routes(self) -> list:
        # Gathers all routes to use.
        routes = []
        for child in self.children:
            routes += child.gather_routes()

        routes += self.routes

        return routes

    def match(self, route: str, method: str = None) -> typing.Tuple[ABCRoute, typing.Iterable]:
        pass
