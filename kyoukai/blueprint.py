"""
A blueprint is a container - a collection of routes.

Kyoukai uses Blueprints to create a routing tree - a tree of blueprints that are used to collect routes together and
match routes easily.
"""
import typing

from werkzeug.routing import Map, Rule

from kyoukai.route import Route

class Blueprint(object):
    """
    A Blueprint class contains a Map of URL rules, which is checked and ran for every
    """

    def __init__(self, name: str, parent: 'Blueprint' = None,
                 prefix: str = ""):
        """
        :param name: The name of this Blueprint.
            This is used when generating endpoints in the finalize stage.

        :param parent: The parent of this Blueprint.
            Parent blueprints will gather the routes of their children, and return a giant :class:`werkzeug.routing.Map`
            object that contains all of the route maps in the children

        :param prefix: The prefix to be added to the start of every route name.
            This is inherited from parents - the parent prefix will also be added to the start of every route.
        """
        self.name = name

        # The parent Blueprint.
        self._parent = parent

        # Any children Blueprints.
        self._children = []

        # The current prefix.
        self._prefix = prefix

        # If this Blueprint is finalized or not.
        # Finalization of a blueprint means gathering all of the Maps, and compiling a routing table which stores the
        # endpoints.
        self._finalized = False

        # The routing table in terms of endpoints.
        # This is automatically copied into the root blueprint at runtime, so using this on blueprnts other than the
        # root one won't do anything.
        self.routing_table = {}

        # This is stored on the root blueprint when the map is ready to be used.
        self._route_map = None  # type: Map

        # This is useless after finalize() is called.
        self._routes_to_add = []

        # The request hook dictionary for this

    @property
    def prefix(self) -> str:
        """
        :return: The combined prefix of this Blueprint.
        """
        if self._parent:
            return self._parent.prefix + self._prefix

        return self._prefix

    def finalize(self):
        """
        Called on the root Blueprint when all Blueprints have been registered and the app is starting.

        This will automatically build a Map of Rule objects for each Blueprint.
        """
        for child in self._children:
            # Update our own routing table.
            self.routing_table.update(**child.routing_table)
            # Update our _routes_to_add.
            self._routes_to_add += child._routes_to_add

        # Make a new Map().
        rule_map = Map(self._routes_to_add)
        self._route_map = rule_map

    def add_child(self, blueprint: 'Blueprint'):
        """
        Adds a Blueprint as a child of this one.

        This is automatically called when using another Blueprint as a parent.
        :param blueprint: The blueprint to add as a child.
        """
        self._children.append(blueprint)
        return blueprint

    def route(self, routing_url: str, methods: typing.Iterable[str] = ("GET",)):
        """
        Convenience decorator for adding a route.

        This is equivalent to:

            route = bp.wrap_route(func)
            bp.add_route(route, routing_url, methods)
        """
        def _inner(func: callable):
            route = self.wrap_route(func)
            self.add_route(route, routing_url, methods)
            return route

        return _inner

    def wrap_route(self, callable) -> Route:
        """
        Wraps a callable in a Route.

        This is required for routes to be added.
        :param callable: The callable to wrap.
        :return: A new :class:`kyoukai.route.Route` object.
        """
        rtt = Route(callable)
        return rtt

    def add_route(self, route, routing_url: str, methods: typing.Iterable[str] = ("GET",)):
        """
        Adds a route to the routing table and map.

        :param route: The route object to add.
            This can be gotten from :class:`kyoukai.blueprints.Blueprints.wrap_route`, or by directly creating a
            Route object.

        :param routing_url: The Werkzeug-compatible routing URL to add this route under.
            For more information, see http://werkzeug.pocoo.org/docs/0.11/routing/.

        :param methods: An iterable of valid method this route can be called with.

        :return: The unmodified route object.
        """
        # Create an endpoint name for the route.
        endpoint = route.get_endpoint_name(self)
        routing_url = self.prefix + routing_url
        route.routing_url = routing_url
        # Create the Rule object for the map.
        rule = Rule(routing_url, methods=methods, endpoint=endpoint)
        # Add it to the routing table.
        self.routing_table[endpoint] = route
        # Add it to the list of routes to add later.
        self._routes_to_add.append(rule)
        return route

    def get_route(self, endpoint: str):
        """
        Gets the route associated with an endpoint.
        """
        return self.routing_table[endpoint]

    def match(self, environment: dict) -> typing.Tuple[Route, typing.Container]:
        """
        Matches with the WSGI environment.

        :param environment: The environment dict to perform matching with.
            You can use the ``environ`` argument of a Request to get the environment back.
        :return: A Route object, which can be invoked to return the right response, and the parameters to invoke it
            with.
        """
        # Get the MapAdapter used for matching.
        adapter = self._route_map.bind_to_environ(environment)
        # Match the route, without catching any exceptions.
        # These exceptions are propagated into the app and handled there instead.
        endpoint, params = adapter.match()

        route = self.get_route(endpoint)

        return route, params
