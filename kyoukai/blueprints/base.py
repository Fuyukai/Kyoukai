"""
The ABC for a Kyoukai Blueprint.

All Blueprint classes should be derived from this class.
"""
import abc
import typing

from kyoukai.routing.base import ABCRoute


class ABCBlueprint(abc.ABC):
    """
    A Blueprint is a container for routes.

    Blueprints have 'parent' blueprints - they inherit error handlers and hooks from them. The root blueprint has no
    parent, so it does not inherit from anything.
    Note that if a Blueprint that is not the root blueprint has a parent value of None, it is automatically set to
    inherit the root blueprint of the app.

    Blueprints allow routes like normal application objects - in fact, the application object's route function is
    implemented with an underlying root blueprint.
    """

    def __init__(self, name: str, parent: 'ABCBlueprint' = None,
                 url_prefix: str = ""):
        """
        :param name: The name of the Blueprint.
        :param parent: The parent Blueprint.
        :param url_prefix: The prefix to append to the matchers of this Blueprint, if applicable.
        """
        self._prefix = url_prefix
        self._name = name
        self._prefix = self._prefix

        self._parent = parent

        self._children = {}

        # Request hooks.
        self.hooks = {}

    # Shared properties across all blueprint classes.

    @property
    def parent(self) -> 'ABCBlueprint':
        """
        :returns: The parent of this blueprint.
        """
        return self._parent

    @parent.setter
    def parent(self, bp: 'ABCBlueprint'):
        """
        Sets the parent blueprint.
        """
        self._parent = bp

    @property
    def children(self) -> typing.List['ABCBlueprint']:
        """
        :returns: A :class:`list` of the children of this blueprint.
        """
        return list(self._children.values())

    @property
    def depth(self) -> int:
        """
        :returns: The depth in the tree this blueprint is at.
        """
        if self._parent is None:
            return 0
        return self._parent.depth + 1

    @property
    def prefix(self) -> str:
        """
        Calculates the prefix using the parent blueprints.
        :return: The full prefix, including the parent prefix.
        """
        if self.parent is None:
            return self._prefix
        return self.parent.prefix + self._prefix

    @property
    def tree_path(self) -> typing.List['ABCBlueprint']:
        """
        :returns: The full tree path to this blueprint.
        """
        if self._parent is None:
            return [self]

        return self._parent.tree_path + [self]

    def add_child(self, child: 'ABCBlueprint'):
        """
        Add a child Blueprint to the current blueprint.

        .. warning::
            This will override the parent of the blueprint, replacing it with this one.

        :param child: The child blueprint.
        """
        if not isinstance(child, self):
            raise TypeError("Blueprints are incompatible")

    @abc.abstractmethod
    def wrap_route(self, match_string: str, coroutine: typing.Awaitable, *, methods: list = None, run_hooks = True) \
            -> ABCRoute:
        """
        Wraps a route in a :class:`Route` object.

        The class that this returns can be configured with the ``route_cls`` attribute of the Blueprint. it is
        automatically called with the specified regular expression.

        :param match_string: The path to match this route on.
                The format of this string depends on the Blueprint class that is being used.

        :param methods: The list of allowed methods, e.g ["GET", "POST"].
                You can check the method with `request.method`.

        :param coroutine: The coroutine handler to take in, which is called when the route is matched.

        :param run_hooks: If pre and post request hooks are ran.

        :return: The new :class:`ABCRoute` object.
        """

    @abc.abstractmethod
    def add_route(self, route: 'ABCRoute'):
        """
        Adds a route to this Blueprint's routing table.

        :param route: The :class:`ABCRoute` to add to the routes.
        """

    def route(self, match_string: str, *, methods: list = None, run_hooks = True):
        """
        Convenience decorator to create a new route.

        This is equivalent to:

        .. code:: python

            route = bp.wrap_route(match_string, callable, methods, run_hooks)
            bp.add_route(route)


       :param match_string: The path to match this route on.
                The format of this string depends on the Blueprint class that is being used.

        :param methods: The list of allowed methods, e.g ["GET", "POST"].
                You can check the method with `request.method`.

        :param run_hooks: Should the pre and post request hooks run automatically?
                This is set to True by default.
        """

        def _add_route_inner(coro):
            route = self.wrap_route(match_string, coro, methods=methods, run_hooks=run_hooks)
            self.add_route(route)
            return route

        return _add_route_inner

    @abc.abstractmethod
    def add_errorhandler(self, code: int, err_handler: ABCRoute):
        """
        Adds an error handler to the dictionary of error handlers for this route.

        :param code: The error code that this error handler should handle.

        :param err_handler: A :class:`Route` object that handles the error.
                Error handlers are just modified routes, so the use of a Route object here is correct.

        :return: The original Route, but with the ``bp`` attribute set to this Blueprint.
        """

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

    @abc.abstractmethod
    def gather_routes(self) -> list:
        """
        Gathers a list of routes from all children.
        :return: A list of route objects.
        """

