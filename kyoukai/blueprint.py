"""
A blueprint is a container - a collection of routes.

Kyoukai uses Blueprints to create a routing tree - a tree of blueprints that are used to collect 
routes together and match routes easily.
"""
import logging

import typing
from werkzeug.exceptions import HTTPException
from werkzeug.routing import Map, Rule, Submount

from kyoukai.route import Route
from kyoukai.routegroup import RouteGroup, get_rg_bp


logger = logging.getLogger("Kyoukai")


class Blueprint(object):
    """
    A Blueprint is a "route container" - it contains 0 to N routes, and 0 to N child Blueprints 
    that inherit from the parent.
    """

    def __init__(self, name: str, parent: 'Blueprint' = None,
                 prefix: str = "", *,
                 host_matching: bool = False, host: str = None):
        """
        :param name: The name of this Blueprint.
            This is used when generating endpoints in the finalize stage.

        :param parent: The parent of this Blueprint.
            Parent blueprints will gather the routes of their children, and return a giant 
            :class:`werkzeug.routing.Map` object that contains all of the route maps in the children

        :param prefix: The prefix to be added to the start of every route name.
            This is inherited from parents - the parent prefix will also be added to the start of 
            every route.
            
        :param host_matching: Should host matching be enabled?
            This is implicitly True if ``host`` is non-None.
            
        :param host: The host of the Blueprint. Used for custom subdomain routing.
            If this is None, then this Blueprint will be used for all hosts.
        """
        #: The name of this Blueprint.
        self.name = name

        #: The parent :class:`~.Blueprint`.
        self._parent = parent

        #: Any children :class:`~.Blueprint` objects.
        self._children = []

        #: The current URL prefix.
        self._prefix = prefix

        #: If this Blueprint is finalized or not.
        #: Finalization of a blueprint means gathering all of the Maps, and compiling a routing
        #: table which stores the endpoints.
        self.finalized = False

        #: The list of routes.
        #: This is used in finalization.
        self.routes = []

        #: The :class:`~werkzeug.routing.Map` used for this blueprint.
        self.map = None  # type: Map

        #: The error handler dictionary.
        self.errorhandlers = {}

        #: The request hooks for this Blueprint.
        self._request_hooks = {}

        #: The host for this Blueprint.
        self._host = host
        self._host_matching = host_matching or self._host is not None

    @property
    def parent(self) -> "Blueprint":
        """
        :return: The parent Blueprint of this blueprint.
        """
        return self._parent

    @property
    def prefix(self) -> str:
        """
        :return: The prefix of this Blueprint.
        
        .. versionchanged:: 2.2.0
        
            Moved prefix combination to :attr:`.computed_prefix`.
        """
        return self._prefix

    @prefix.setter
    def prefix(self, value):
        self._prefix = value

    @property
    def computed_prefix(self) -> str:
        """
        :return: The combined prefix (parent + ours) of this Blueprint.
        
        .. versionadded:: 2.2.0
        """
        if self._parent:
            return self._parent.computed_prefix + self._prefix

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

    @property
    def host(self) -> str:
        """
        :return: The host for this Blueprint, or the host of any parent Blueprint. 
        """
        if self._parent:
            return self._host or self.parent.host

        return self._host

    def get_submount(self) -> Submount:
        """
        Gets the :class:`werkzeug.routing.Submount` for this Blueprint.
        
        .. versionadded:: 2.2.0
        """
        inner = []
        # get child submounts
        for bp in self._children:
            inner.append(bp.get_submount())

        # get route submounts
        for route in self.routes:
            inner.append(route.get_submount())

        # create the submount
        sm = Submount(self._prefix,
                      rules=inner)

        return sm

    def traverse_tree(self) -> 'typing.Generator[Blueprint, None, None]':
        """
        Traverses the tree for children Blueprints.
        """
        for child in self._children:
            yield from child.traverse_tree()
            yield child

    def finalize(self, **map_options) -> Map:
        """
        Called on the root Blueprint when all Blueprints have been registered and the app is 
        starting.
        
        This will automatically build a :class:`werkzeug.routing.Map` of 
        :class:`werkzeug.routing.Rule` objects for each Blueprint.
        
        .. note::
        
            Calling this on sub-blueprints will have no effect, apart from generating a Map.  
            It is recommended to only call this on the root Blueprint.
            
        .. versionchanged:: 2.2.0
        
            This now uses submounts instead of a giant rule amalgamation.
        
        :param map_options: The options to pass to the created Map.
        :return: The :class:`werkzeug.routing.Map` created from the routing tree.
        """
        if self.finalized is True:
            return self.map

        submount = self.get_submount()
        logger.info("Scanned {} route(s) in the routing tree, building routing mapping."
                    .format(sum(1 for x in submount.get_rules(submount))))

        # Make a new Map() out of all of the routes.
        rule_map = Map([submount], host_matching=self._host_matching, **map_options)

        logger.info("Built route mapping with {} rules.".format(len(rule_map._rules)))

        # update self.map
        self.map = rule_map
        self.finalized = True

        return rule_map

    def add_child(self, blueprint: 'Blueprint') -> 'Blueprint':
        """
        Adds a Blueprint as a child of this one.
        This is automatically called when using another Blueprint as a parent.
        
        :param blueprint: The blueprint to add as a child.
        """
        self._children.append(blueprint)
        blueprint._parent = self
        return blueprint

    def route(self, routing_url: str, methods: typing.Sequence[str] = ("GET", "HEAD"),
              **kwargs):
        """
        Convenience decorator for adding a route.

        This is equivalent to:

        .. code-block:: python
        
            route = bp.wrap_route(func, **kwargs)
            bp.add_route(route, routing_url, methods)
           
        .. versionchanged:: 2.2.0
        
            Now accepts a Route as the function to decorate - this will add a new routing url and 
            method pair to :meth:`.Route.add_route`.
        """

        def _inner(func):
            if isinstance(func, Route):
                # don't re-wrap, only add the routing URL and methods
                func.add_path(routing_url, methods)
                return func

            route = self.wrap_route(func, **kwargs)
            self.add_route(route, routing_url, methods)
            return route

        return _inner

    def errorhandler(self, code: int, endcode: int = None, step: int = None):
        """
        Helper decorator for adding an error handler.

        This is equivalent to:

        .. code-block:: python

            route = bp.add_errorhandler(cbl, code)

        :param code: The error handler code to use.
        :param endcode: The end of the error code range to handle. Error handlers will be added \
            for all requests between code and endcode. If this is not provided, only one code \
            will be handled.

        :param step: The step for the error handler range.
        """

        def _inner(cbl):
            self.add_errorhandler(cbl, code, endcode, step)
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

    def add_errorhandler(self, cbl, startcode: int, endcode: int = None, step: int = None):
        """
        Adds an error handler to the table of error handlers.

        A blueprint can only have one error handler per code. If it doesn't have an error handler 
        for that code, it will try to fetch recursively the parent's error handler.

        :param cbl: The callable error handler.
        :param startcode: The error code to handle, for example 404.
            This also represents the start of an error range, if endcode is not None.
        :param endcode: The end of the error code range to handle. Error handlers will be added \
            for all requests between startcode and endcode.
        :param step: The step for the error handler range.
        """
        # don't re-wrap it in a route if it's already a route
        rtt = cbl
        if not isinstance(rtt, Route):
            rtt = self.wrap_route(rtt, should_invoke_hooks=False)

        # if it's a single code, just use the one error handler
        if endcode is None:
            self.errorhandlers[startcode] = rtt
        else:
            # add a range of routes instead
            for i in range(startcode, endcode, step or 1):
                self.errorhandlers[i] = rtt

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

    def add_route(self, route: Route, routing_url: str,
                  methods: typing.Sequence[str] = ("GET", "HEAD")):
        """
        Adds a route to the routing table and map.

        :param route: The route object to add.
        
            This can be gotten from :class:`.Blueprint.wrap_route`, or by 
            directly creating a Route object.

        :param routing_url: The Werkzeug-compatible routing URL to add this route under.
                    
            For more information, see http://werkzeug.pocoo.org/docs/0.11/routing/.

        :param methods: An iterable of valid method this route can be called with.

        :return: The unmodified :class:`~.Route` object.
        """
        # Add the routing path to the route
        route.add_path(routing_url, methods)
        # Add it to the list of routes to add later.
        self.routes.append(route)
        # Add the self to the route.
        route.bp = self

        return route

    def get_route(self, endpoint: str) -> 'typing.Union[Route, None]':
        """
        Gets the route associated with an endpoint.
        """
        for route in self.tree_routes:
            if route.get_endpoint_name() == endpoint:
                return route

        return None

    def add_route_group(self, group: 'RouteGroup'):
        """
        Adds a route group to the current Blueprint.
        
        :param group: The :class:`~.RouteGroup` to add. 
        """
        bp = get_rg_bp(group)
        self.add_child(bp)

        return self

    def url_for(self, environment: dict, endpoint: str, *,
                method: str = None, **kwargs) -> str:
        """
        Gets the URL for a specified endpoint using the arguments of the route.

        This works very similarly to Flask's ``url_for``.

        It is not recommended to invoke this method directly - instead, ``url_for`` is set on the 
        context object that is provided to your user function. This will allow you to invoke it 
        with the correct environment already set.

        :param environment: The WSGI environment to use to bind to the adapter.
        :param endpoint: The endpoint to try and retrieve.

        :param method: If set, the method to explicitly provide (for similar endpoints with \ 
            different allowed routes).

        :param kwargs: Keyword arguments to provide to the route.
        :return: The built URL for this endpoint.
        """
        bound = self.map.bind_to_environ(environment)

        # Build the URL from the endpoint.
        built_url = bound.build(endpoint, values=kwargs, method=method)

        return built_url

    def match(self, environment: dict) -> typing.Tuple[Route, typing.Container[typing.Any], Rule]:
        """
        Matches with the WSGI environment.
        
        .. warning::
            You should **not** be using this method yourself.
            
        .. versionchanged:: 2.2.0
            This will now return the :class:`werkeug.routing.Rule` as well.

        :param environment: The environment dict to perform matching with.
            You can use the ``environ`` argument of a Request to get the environment back.
            
        :return: A Route object, which can be invoked to return the right response, and the \
            parameters to invoke it with.
        """
        # Get the MapAdapter used for matching.
        adapter = self.map.bind_to_environ(environment)
        # Match the route, without catching any exceptions.
        # These exceptions are propagated into the app and handled there instead.
        rule, params = adapter.match(return_rule=True)

        route = self.get_route(rule.endpoint)

        return route, params, rule
