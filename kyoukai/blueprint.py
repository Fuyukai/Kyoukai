"""
A blueprint is a container - a collection of routes.

Kyoukai uses Blueprints to create a routing tree - a tree of blueprints that are used to collect routes together and
match routes easily.
"""
import typing
from kyoukai.routegroup import RouteGroup, get_rg_bp

from werkzeug.exceptions import HTTPException
from werkzeug.routing import Map, Rule
from werkzeug.wrappers import Response

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
        #: The name of this Blueprint.
        self.name = name

        #: The parent :class:`~.Blueprint`.
        self._parent = parent

        #: Any children :class:`~.Blueprint` objects.
        self._children = []

        # The current prefix.
        self._prefix = prefix

        #: If this Blueprint is finalized or not.
        #: Finalization of a blueprint means gathering all of the Maps, and compiling a routing
        #: table which stores the endpoints.
        self.finalized = False

        #: The list of routes.
        #: This is used in finalization.
        self.routes = []

        #: The :class:`~werkzeug.routing.Map` used for this blueprint.
        self._route_map = None  # type: Map

        #: The error handler dictionary.
        self.errorhandlers = {}

        #: The request hooks for this Blueprint.
        self._request_hooks = {}

    @property
    def parent(self) -> "Blueprint":
        """
        :return: The parent Blueprint of this blueprint.
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

    @property
    def tree_routes(self) -> 'typing.Generator[Route, None, None]':
        """
        :return: A generator that yields all routes from the tree, from parent to children.
        """
        for route in self.routes:
            yield route

        for child in self._children:
            yield from child.tree_routes

    def finalize(self):
        """
        Called on the root Blueprint when all Blueprints have been registered and the app is starting.

        This will automatically build a Map of Rule objects for each Blueprint.
        """
        routes = self.routes.copy()
        for child in self._children:
            routes.extend(list(child.tree_routes))

        # Make a new Map() out of all of the routes.
        rule_map = Map([route.create_rule() for route in routes])
        self._route_map = rule_map

        self.finalized = True

    def add_child(self, blueprint: 'Blueprint') -> 'Blueprint':
        """
        Adds a Blueprint as a child of this one.

        This is automatically called when using another Blueprint as a parent.
        :param blueprint: The blueprint to add as a child.
        """
        self._children.append(blueprint)
        blueprint._parent = self
        return blueprint

    def route(self, routing_url: str, methods: typing.Iterable[str] = ("GET",),
              **kwargs):
        """
        Convenience decorator for adding a route.

        This is equivalent to:

            route = bp.wrap_route(func)
            bp.add_route(route, routing_url, methods)
        """

        def _inner(func):
            route = self.wrap_route(func, **kwargs)
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

        def _inner(cbl):
            self.add_errorhandler(cbl, code)
            return cbl

        return _inner

    def wrap_route(self, cbl, *args, **kwargs) -> Route:
        """
        Wraps a callable in a Route.

        This is required for routes to be added.
        :param cbl: The callable to wrap.
        :return: A new :class:`~.Route` object.
        """
        rtt = Route(cbl, *args, **kwargs)
        return rtt

    def add_errorhandler(self, cbl, errorcode: int):
        """
        Adds an error handler to the table of error handlers.

        A blueprint can only have one error handler per code. If it doesn't have an error handler for that code,
        it will try to fetch recursively the parent's error handler.

        :param cbl: The callable error handler.
        :param errorcode: The error code to handle, for example 404.
        """
        # for simplicity sake, wrap it in a route.
        rtt = self.wrap_route(cbl, should_invoke_hooks=False)
        self.errorhandlers[errorcode] = rtt
        rtt.bp = self
        return rtt

    def get_errorhandler(self, exc: typing.Union[HTTPException, int]) -> typing.Union[None, Route]:
        """
        Recursively acquires the error handler for the specified error.
        
        :param exc: The exception to get the error handler for.
            This can either be a HTTPException object, or an integer.

        :return: The :class:`~.Route` object that corresponds to the error handler, \ 
            or None if no error handler could be found.
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

    def get_hooks(self, type_: str):
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

    def add_hook(self, type_: str, hook):
        """
        Adds a hook to the current Blueprint.

        :param type_: The type of hook to add (currently "pre" or "post").
        :param hook: The callable function to add as a hook.
        """
        if type_ not in self._request_hooks:
            self._request_hooks[type_] = []

        self._request_hooks[type_].append(hook)
        return hook

    def after_request(self, func):
        """
        Convenience decorator to add a post-request hook.
        """
        return self.add_hook(type_="post", hook=func)

    def before_request(self, func):
        """
        Convenience decorator to add a pre-request hook.
        """
        return self.add_hook(type_="pre", hook=func)

    def add_route(self, route: Route, routing_url: str, methods: typing.Iterable[str] = ("GET",)):
        """
        Adds a route to the routing table and map.

        :param route: The route object to add.
        
            This can be gotten from :class:`kyoukai.blueprints.Blueprints.wrap_route`, or by 
            directly creating a Route object.

        :param routing_url: The Werkzeug-compatible routing URL to add this route under.
                    
            For more information, see http://werkzeug.pocoo.org/docs/0.11/routing/.

        :param methods: An iterable of valid method this route can be called with.

        :return: The unmodified :class:`~.Route` object.
        """
        # Create an endpoint name for the route.
        route.routing_url = routing_url
        route.methods = methods
        # Add it to the list of routes to add later.
        self.routes.append(route)
        # Add the self to the route.
        route.bp = self

        return route

    def get_route(self, endpoint: str):
        """
        Gets the route associated with an endpoint.
        """
        for route in self.tree_routes:
            if route.get_endpoint_name() == endpoint:
                return route

        return None

    def add_route_group(self, group: 'RouteGroup', *args, **kwargs):
        """
        Adds a route group to the current Blueprint.
        
        :param group: The :class:`~.RouteGroup` to add. 
        """
        bp = get_rg_bp(group)
        self.add_child(bp)

        return self

    def url_for(self, environment: dict, endpoint: str,
                *,
                method: str = None,
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
            
        :return: A Route object, which can be invoked to return the right response, and the parameters to invoke it \
            with.
        """
        # Get the MapAdapter used for matching.
        adapter = self._route_map.bind_to_environ(environment)
        # Match the route, without catching any exceptions.
        # These exceptions are propagated into the app and handled there instead.
        endpoint, params = adapter.match()

        route = self.get_route(endpoint)

        return route, params
