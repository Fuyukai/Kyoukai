"""
Kyōkai blueprints are simply groups of routes.

They're a simpler way of grouping your routes together instead of having to import your app object manually all of
the time.
"""
import collections
import logging

import re
import typing

from kyoukai.exc import HTTPException
from kyoukai.route import Route
from kyoukai.views import View


class Blueprint(object):
    """
    A Blueprint is a container for routes.

    Blueprints have 'parent' blueprints - they inherit error handlers and hooks from them. The root blueprint has no
    parent, so it does not inherit from anything.
    Note that if a Blueprint that is not the root blueprint has a parent value of None, it is automatically set to
    inherit the root blueprint of the app.

    Blueprints allow routes like normal application objects - in fact, the application object's route function is
    implemented with an underlying root blueprint.

    .. code:: python

        bp = Blueprint("test_bp")

        @bp.route("/hello/world")
        async def hello_world(ctx: HTTPRequestContext):
            return "Hello, world"!

    Per-blueprint error handlers can also be added:

    .. code:: python

        @bp.errorhandler(500)
        async def handle_500(ctx: HTTPRequestContext, e: Exception):
            async with threadpool():
                ctx.dbsession.rollback()

    :param name: The name identifier of the blueprint.
    :param parent: The parent blueprint.
        Children blueprint inherit routes from the parent, accessible via ``Parent.routes``.
        They are also used for searching in routes when a blueprint is checked.

        If this is None, then it will be automatically set when the blueprint is added as a child to a parent
        blueprint.

        The only Blueprint that should have no parent during the run time of the app is the root blueprint.

    :param url_prefix: The prefix to automatically add to the start of each route.

    :cvar route_cls: The Route class to use for wrapping new Routes.
    """

    route_cls = Route

    def __init__(self, name: str, parent: 'Blueprint' = None,
                 url_prefix: str = ""):
        self._prefix = url_prefix
        self._name = name

        self.routes = []

        self.errhandlers = {}

        # The parent of this blueprint.
        self._parent = parent
        if self._parent is not None:
            # Add ourselves as a child.
            self._parent.add_child(self)

        # The children of this blueprint.
        self._children = {}

        self._request_hooks = collections.defaultdict(lambda *args, **kwargs: collections.OrderedDict())

        self.logger = logging.getLogger("Kyoukai.Blueprint." + self._name if self._name else "root")

    def __len__(self):
        """
        Gets the number of routes attached to this Blueprint.

        This takes into account children routes.
        """
        tmplen = len(self.routes)
        for child in self.children.values():
            tmplen += len(child)

        return tmplen

    def bind_view(self, view: View, *args, **kwargs):
        """
        Binds a view class to a Blueprint.

        This takes the *class*, not the instance, as a param.

        It also takes args and keyword args to instantiate the class with.
        """
        # Create a new instance of the class.
        new_view = view(*args, **kwargs)
        # Don't bind if it's already binded.
        if new_view._binded:
            return
        for route in view.get_routes():
            route.bp = self
            self.routes.append(route)

        # Add before_request and after_request from the new_view.
        def __wrapper(func):
            async def ___internal_wrapper(*args, **kwargs):
                await func(*args, **kwargs)

            return ___internal_wrapper

        if hasattr(new_view, "before_request"):
            # Create wrappers for the new views.
            nf = __wrapper(new_view.before_request)
            nf.__name__ = new_view.__class__.__name__ + ".before_request"
            self.before_request(nf)

        if hasattr(new_view, "after_request"):
            # Create wrappers for the new view.
            nf = __wrapper(new_view.after_request)
            nf.__name__ = new_view.__class__.__name__ + ".after_request"
            self.after_request(nf)

        self.logger.info("Bound view {}".format(view.__name__))

    def __repr__(self):
        return "<Blueprint '{}' with {} routes>".format(self._name, len(self.routes))

    def add_child(self, blueprint: 'Blueprint'):
        """
        Add a child Blueprint to the current blueprint.

        .. warning::
            This will override the parent of the blueprint, replacing it with this one.

        :param blueprint: The child blueprint.
        """
        self._children[blueprint._name] = blueprint
        self.logger.info("Registered Blueprint {} with {} new routes".format(blueprint._name, len(blueprint)))
        blueprint.parent = self

    def before_request(self, coro):
        """
        Set a coroutine to run as before the request.

        This coroutine should take in the HTTPRequestContext, and return a new HTTPRequestContext.
        """
        # Unlike before, don't use Route objects.
        # Just append it to the route handlers.
        self._request_hooks["pre"][coro.__name__] = coro
        return coro

    def after_request(self, coro):
        """
        Set a coroutine to run after the request.

        This coroutine should take in a :class:`Response`, and return a :class:`Response`.
        """
        self._request_hooks["post"][coro.__name__] = coro
        return coro

    def get_pre_hooks(self, ctx):
        """
        Get the pre-request hooks in a list.

        This goes from top-level blueprint to bottom-level blueprint in terms of order.

        :param ctx: The context of the request.
        """
        if self.parent is not None:
            bps = self.parent.get_pre_hooks(ctx)
        else:
            bps = []

        # Return the list of our hooks, merged with the other list.
        return bps + list(self._request_hooks["pre"].values())

    def get_post_hooks(self, ctx):
        """
        Get the post-request hooks in a list.

        This goes from top-level blueprint to bottom-level blueprint in terms of order.

        :param ctx: The context of the request.
        """
        if self.parent is not None:
            bps = self.parent.get_post_hooks(ctx)
        else:
            bps = []

        # Return the list of our hooks, merged with the other list.
        return bps + list(self._request_hooks["post"].values())

    def gather_routes(self, route: str, method: str) -> typing.List[Route]:
        """
        Gathers a list of routes from all children which match the specified path.

        This will traverse down all children blueprints, and call .match() on them.
        Then it will traverse down our routes, and check if the routes match.

        .. versionadded:: 1.8.5

        :param route: The path to match.
        :param method: The method to match. Used only for `HEAD` and `ANY` matching.
        :return: A list of routes that matched.
        """
        matches = []
        for route_obb in self.routes:
            assert isinstance(route_obb, Route)
            matched = route_obb.match(route, method)
            if matched:
                matches.append(matched)

        # Gather the routes on the children.
        for child in self.children.values():
            matched = child.gather_routes(route, method)
            if matched:
                matches += matched

        return matches

    def match(self, route: str, method: str):
        """
        Match a route.

        This will search down our routes, and then down our children's routes, to see if we can find a match for the
        specified route.

        .. versionchanged:: 1.8.5

            This is now effectively only used on the root blueprint. Children blueprints should have this called
            explicitly by other handlers to match routes only on those blueprints.

        :param route: The route to match, e.g ``/abc/def``.
        :param method: The method of the route.

        :raises: A :class:`kyoukai.exc.HTTPException` with code 415 if the method is not valid.
        :returns: The :class:`Route` if the route was matched, or None.
        """
        matches = self.gather_routes(route, method)

        if not matches:
            return None
        else:
            # Loop through each route, and check the method.
            # If no method matches, then raise the HTTPException. Otherwise, return the route.
            # This allows for multiple routes with the same method.
            for route in matches:
                if route.kyokai_method_allowed(method):
                    return route
            else:
                # This is called when no return successfully hit.
                raise HTTPException(405)

    @property
    def parent(self) -> 'Blueprint':
        """
        :returns: The parent of this blueprint.
        """
        return self._parent

    @parent.setter
    def parent(self, bp: 'Blueprint'):
        """
        Sets the parent blueprint.
        """
        self._parent = bp

    @property
    def children(self):
        """
        :returns: A :class:`list` of the children of this blueprint.
        """
        return self._children

    @property
    def depth(self) -> int:
        """
        :returns: The depth in the tree this blueprint is at.
        """
        if self._parent is None:
            return 0
        return self._parent.depth + 1

    @property
    def prefix(self):
        """
        Calculates the prefix using the parent blueprints.
        :return: The full prefix, including the parent prefix.
        """
        if self.parent is None:
            return self._prefix
        return self.parent.prefix + self._prefix

    def wrap_route(self, regex, coroutine, *, methods: list = None, run_hooks=True):
        """
        Wraps a route in a :class:`Route` object.

        The class that this returns can be configured with the ``route_cls`` attribute of the Blueprint. it is
        automatically called with the specified regular expression.

        :param regex: The regular expression to match the path to. This uses standard Python :mod:`re` syntax.
                Group matches are automatically extracted from the regex, and passed as arguments.

        :param methods: The list of allowed methods, e.g ["GET", "POST"].
                You can check the method with `request.method`.

        :param coroutine: The coroutine handler to take in, which

        :param run_hooks: If pre and post request hooks are ran.

        :return: The new :class:`Route` object.
        """
        if not methods:
            methods = ["GET"]

        r = self.route_cls(self, regex, methods, run_hooks=run_hooks)
        r.create(coroutine)

        return r

    def add_route(self, route: Route):
        """
        Adds a route object to the routing table.

        .. note::

            This will set the blueprint of the specified route to ourselves, overwriting any other routes.

        :param route: The route object to add.
        :return: The Route.
        """
        route.bp = self
        self.routes.append(route)

        return route

    def route(self, regex, *, methods: list = None, run_hooks=True):
        """
        Convenience decorator to create a new route.

        This is equivalent to:

        .. code:: python

            route = bp.wrap_route(regex, callable, methods, run_hooks)
            bp.add_route(route)


        :param regex: The regular expression to match the path to. This uses standard Python :mod:`re` syntax.
                Group matches are automatically extracted from the regex, and passed as arguments.

        :param methods: The list of allowed methods, e.g ["GET", "POST"].
                You can check the method with `request.method`.

        :param run_hooks: Should the pre and post request hooks run automatically?
                This is set to True by default.
        """

        def _add_route_inner(coro):
            route = self.wrap_route(regex, coro, methods=methods, run_hooks=run_hooks)
            self.add_route(route)
            return route

        return _add_route_inner

    def get_errorhandler(self, code: int) -> Route:
        """
        Not to be used by the user/dev - internal function used to traverse down the parent's error handlers.
        """
        err_handler = self.errhandlers.get(code)

        if err_handler:
            return err_handler

        if self.parent is None:
            # We can't get the parent's error handler, oh well.
            return None

        return self.parent.get_errorhandler(code)

    def add_errorhandler(self, code: int, err_handler: Route):
        """
        Adds an error handler to the dictionary of error handlers for this route.

        :param code: The error code that this error handler should handle.

        :param err_handler: A :class:`Route` object that handles the error.
                Error handlers are just modified routes, so the use of a Route object here is correct.

        :return: The original Route, but with the ``bp`` attribute set to this Blueprint.
        """
        err_handler.bp = self
        self.errhandlers[code] = err_handler

        return err_handler

    def errorhandler(self, code: int, run_hooks=False):
        """
        Convenience decorator to add an error handler.

        This is equivalent to:

        .. code:: python

            route = bp.wrap_route("", coro, methods=[], run_hooks=False)
            bp.add_errorhandler(code, route)
        """

        def _add_route_inner(coro):
            route = self.wrap_route("", coro, methods=[], run_hooks=run_hooks)
            self.add_errorhandler(code, route)
            return route

        return _add_route_inner
