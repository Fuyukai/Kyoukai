"""
Werkzeug-based blueprints for Kyoukai.
"""
import typing

from kyoukai.blueprints.base import ABCBlueprint
from kyoukai.routing.base import ABCRoute
from kyoukai.routing.werkzeug import WerkzeugRoute

from werkzeug.routing import RuleFactory, Map, Submount


class RuleFactoryMap(RuleFactory, Map):
    """
    A RuleFactory which is also a Map.
    """

    def __init__(self, rules=[]):
        super().__init__((rule.empty() for rule in rules))

    def get_rules(self, map):
        for rulefactory in self:
            for rule in rulefactory.get_rules(map):
                rule = rule.empty()
                yield rule


class WerkzeugBlueprint(ABCBlueprint):
    """
    The class for a Werkzeug-based blueprint. Wraps `werkzeug.routing.Map`.
    """

    def __init__(self, name: str, parent: 'ABCBlueprint' = None,
                 url_prefix: str = ""):
        super().__init__(name, parent, url_prefix)
        self.url_prefix = url_prefix

        #: Define the routes list.
        self.routes = []

        #: Define the dictionary of error handlers.
        self.errorhandlers = {}

    def add_route(self, route: 'WerkzeugRoute'):
        # Adds the route to self.route
        self.routes.append(route.matcher.empty())
        return route

    def wrap_route(self, match_string: str, coroutine: typing.Awaitable, *, methods: list = None,
                   run_hooks=True) -> ABCRoute:
        rtt = WerkzeugRoute(self, match_string, methods, bound=False, run_hooks=run_hooks)
        rtt.create(coroutine)

        return rtt

    def add_errorhandler(self, code: int, err_handler: ABCRoute):
        err_handler.bp = self
        self.errorhandlers[code] = err_handler

    def gather_routes(self) -> RuleFactory:
        if self.url_prefix:
            return RuleFactoryMap(Submount(self.url_prefix, self.routes))

        return RuleFactoryMap(self.routes)

    def get_errorhandler(self, code: int):
        if code in self.errorhandlers:
            return self.errorhandlers[code]

        if self.parent is None:
            return None

        return self.parent.get_errorhandler(code)
