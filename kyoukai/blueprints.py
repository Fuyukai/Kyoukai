"""
Kyōkai blueprints are simply groups of routes.

They're a simpler way of grouping your routes together instead of having to import your app object manually all of
the time.
"""
import collections

import re

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

    :param name: The name identifier of the blueprint.
    :param parent: The parent blueprint.
        Children blueprint inherit routes from the parent, accessible via ``Parent.routes``.
        They are also used for searching in routes when a blueprint is checked.

        If this is None, then it will be automatically set when

    :param url_prefix: The prefix to automatically add to the start of each route.
    """

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
            route.matcher = re.compile(self.prefix + route._match_str)
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

    def __repr__(self):
        return "<Blueprint '{}' with {} routes>".format(self._name, len(self.routes))

    def add_child(self, blueprint: 'Blueprint'):
        """
        Add a child Blueprint to the current blueprint.

        .. note:
            This will override the parent of the blueprint, replacing it with this one.

        :param blueprint: The child blueprint.
        """
        self._children[blueprint._name] = blueprint
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

    def match(self, route: str, method: str):
        """
        Match a route.

        This will search down our routes, and then down our children's routes, to see if we can find a match for the
        specified route.

        :param route: The route to match, e.g ``/abc/def``.
        :param method: The method of the route.

        :raises: A :class:`kyoukai.exc.HTTPException` with code 415 if the method is not valid.
        :returns: The :class:`Route` if the route was matched, or None.
        """
        matches = []
        for route_obb in self.routes:
            assert isinstance(route_obb, Route)
            matched = route_obb.match(route, method)
            if matched:
                matches.append(matched)

        # Search through the children
        for child in self.children.values():
            matched = child.match(route, method)
            if matched:
                matches.append(matched)

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
    def prefix(self):
        """
        Calculates the prefix using the parent blueprints.
        """
        if self.parent is None:
            return self._prefix
        return self.parent.prefix + self._prefix

    def route(self, regex, *, methods: list = None, run_hooks=True):
        """
        Create an incoming route for a function.

        :param regex: The regular expression to match the path to. This uses standard Python :mod:`re` syntax.
                Group matches are automatically extracted from the regex, and passed as arguments.

        :param methods: The list of allowed methods, e.g ["GET", "POST"].
                You can check the method with `request.method`.
        """
        if not methods:
            methods = ["GET"]
        regex = self.prefix + regex
        r = Route(self, regex, methods, run_hooks=run_hooks)
        self.routes.append(r)
        return r

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

    def errorhandler(self, code: int, run_hooks=False):
        """
        Create an error handler for the specified code.

        This will wrap the function in a Route.
        """
        r = Route(self, "", [], run_hooks=run_hooks)
        self.errhandlers[code] = r
        return r
