"""
A blueprint is a container - a collection of routes.

Kyoukai uses Blueprints to create a routing tree - a tree of blueprints that are used to collect routes together and
match routes easily.
"""
import typing

from werkzeug.exceptions import HTTPException
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
        self.finalized = False

        # The routing table in terms of endpoints.
        # This is automatically copied into the root blueprint at runtime, so using this on blueprnts other than the
        # root one won't do anything.
        self.routing_table = {}

        # This is stored on the root blueprint when the map is ready to be used.
        self._route_map = None  # type: Map

        # This is useless after finalize() is called.
        self._routes_to_add = []

        # The error handler dictionary.
        self.errorhandlers = {}

        # The request hooks for this Blueprint.
        self._request_hooks = {}

    @property
    def parent(self) -> "Blueprint":
        """
        Gets the parent Blueprint of this blueprint.
        """
        return self._parent

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

        self.finalized = True

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

    def errorhandler(self, code: int):
        """
        Helper decorator for adding an error handler.

        This is equivalent to:

            route = bp.add_errorhandler(cbl, code)

        :param code: The error handler code to use.
        """
        def _inner(cbl: typing.Callable):
            self.add_errorhandler(cbl, code)
            return cbl

        return _inner

    def wrap_route(self, cbl: typing.Callable) -> Route:
        """
        Wraps a callable in a Route.

        This is required for routes to be added.
        :param cbl: The callable to wrap.
        :return: A new :class:`kyoukai.route.Route` object.
        """
        rtt = Route(cbl)
        return rtt

    def add_errorhandler(self, cbl: typing.Callable, errorcode: int):
        """
        Adds an error handler to the table of error handlers.

        A blueprint can only have one error handler per code. If it doesn't have an error handler for that code,
        it will try to fetch recursively the parent's error handler.

        :param cbl: The callable error handler.
        :param errorcode: The error code to handle, for example 404.
        """
        # for simplicity sake, wrap it in a route.
        rtt = self.wrap_route(cbl)
        self.errorhandlers[errorcode] = rtt
        rtt.bp = self
        return rtt

    def get_errorhandler(self, exc: typing.Union[HTTPException, int]) -> typing.Union[None, Route]:
        """
        Recursively acquires the error handler for
        :param exc: The exception to get the error handler for.
            This can either be a HTTPException object, or an integer.

        :return: The :class:`kyoukai.route.Route` object that corresponds to the error handler, or None if no error
        handler could be found.
        """
        if isinstance(exc, HTTPException):
            exc = exc.code

        try:
            return self.errorhandlers[exc]
        except KeyError:
            try:
                return self._parent.get_errorhandler(exc)
            except (KeyError, AttributeError):
                return None

    def get_hooks(self, type_: str) -> typing.Iterable:
        """
        Gets a list of hooks that match the current type.

        These are ordered from parent to child.

        :param type_: The type of hooks to get (currently "pre" or "post").
        :return: An iterable of hooks to run.
        """
        hooks = []
        if self._parent:
            hooks.extend(self._parent.get_hooks(type_))

        hooks.extend(self._request_hooks.get(type_, []))

        return hooks

    def add_hook(self, type_: str, hook: typing.Callable) -> typing.Callable:
        """
        Adds a hook to the current Blueprint.

        :param type_: The type of hook to add (currently "pre" or "post").
        :param hook: The callable function to add as a hook.
        """
        if type_ not in self._request_hooks:
            self._request_hooks[type_] = []

        self._request_hooks.append(hook)
        return hook

    def after_request(self, func: typing.Callable):
        """
        Convenience decorator to add a post-request hook.
        """
        return self.add_hook(type_="post", hook=func)

    def before_request(self, func: typing.Callable):
        """
        Convenience decorator to add a pre-request hook.
        """
        return self.add_hook(type_="pre", hook=func)

    def add_route(self, route: Route, routing_url: str, methods: typing.Iterable[str] = ("GET",)):
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
        # Add the rule to the route.
        route.rule = rule
        route.bp = self

        return route

    def get_route(self, endpoint: str):
        """
        Gets the route associated with an endpoint.
        """
        return self.routing_table[endpoint]

    def url_for(self, environment: dict, endpoint: str,
                *,
                method: str=None,
                **kwargs) -> str:
        """
        Gets the URL for a specified endpoint using the arguments of the route.

        This works very similarly to Flask's ``url_for``.

        It is not recommended to invoke this method directly - instead, ``url_for`` is set on the context object that
        is provided to your user function. This will allow you to invoke it with the correct environment already set.

        :param environment: The WSGI environment to use to bind to the adapter.
        :param endpoint: The endpoint to try and retrieve.

        :param method: If set, the method to explicitly provide (for similar endpoints with different allowed routes).

        :param kwargs: Keyword arguments to provide to the route.
        :return: The built URL for this endpoint.
        """
        bound = self._route_map.bind_to_environ(environment)

        # Build the URL from the endpoint.
        built_url = bound.build(endpoint, values=kwargs, method=method)

        return built_url

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
