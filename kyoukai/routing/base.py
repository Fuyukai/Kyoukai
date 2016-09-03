"""
Defines the ABC for a router.
"""

import abc
import typing

import kyoukai.app
from kyoukai import HTTPRequestContext


class ABCRoute(abc.ABC):
    """
    A route is a wrapped coroutine object. It provides utilities that allows Kyoukai to interact with the bare route
    command more easily.

    :param blueprint: The blueprint this route is associated with.
    :param matcher: The match string used to create this route.
        This will vary depending on the router.

    :param methods: A :class:`list` of methods that are allowed in this route.
    :param bound: Internal. Used for views.
    :param run_hooks: If the request should run pre and post hooks, or be exempt.
    """

    def __init__(self, blueprint,
                 matcher: str, methods: list,
                 bound: bool = False,
                 run_hooks: bool = True):
        """
        Create a new Route.
        """
        self._match_str = matcher
        self.allowed_methods = methods
        self._wrapped_coro = None

        self.bp = blueprint

        # Used for bounded routes.
        self._bound = bound

        self._view_class = None

        self.name = "<Undefined route>"

        self._should_run_hooks = run_hooks

    @abc.abstractmethod
    async def invoke(self, ctx: HTTPRequestContext, args: typing.Iterable=None, exception: Exception=None):
        """
        Invokes the route, running it.

        :param ctx: The current HTTP context for the route.
        :param args: The expanded arguments from the route, placed into the
        :param exception: Called on an error handler. Is None otherwise.

        :return: The :class:`Response` created.
        """

    def __call__(self, coro):
        """
        Sets the coroutine.
        """
        return self.create(coro)

    def create(self, coro):
        """
        Creates a route from the coroutine.
        """
        self._wrapped_coro = coro
        self.name = coro.__name__
        return self

    # Used for bound routes.
    @property
    def self(self):
        if self._bound:
            return self._view_class
        else:
            return

    @self.setter
    def self(self, vc):
        if self._bound:
            self._view_class = vc
        else:
            raise TypeError("Attempted to update view class on unbounded route")


class ABCRouter(abc.ABC):
    """
    A router defines how routes are routed from an incoming client connection.

    Before 1.10, routes were purely routed based on a regular expression. In 1.10 and above, the Router is
    responsible for routing, which (by default) is a regular expression but can be extended to use something like the
    Werkzeug router.
    """

    def __init__(self, app: 'kyoukai.app.Kyoukai'):
        self.app = app

    @staticmethod
    def calculate_405_errorhandler(routes: list):
        """
        Calculates what Blueprint the 405 error handler should run on.

        :param routes: A list of route objects to run on.
        :return: The top-most blueprint to use.
        """
        common_blueprints = None
        for route in routes:
            full_match = set(route.bp.tree_path)
            # If common_blueprints is defined, we can do an intersection on it.
            # Otherwise, we just set it to the current set of Blueprints.
            if common_blueprints is not None:
                common_blueprints = common_blueprints.intersection(full_match)
            else:
                common_blueprints = full_match

        # Turn that set back into a list, and sort it by depth.
        cmn_bp = list(common_blueprints)
        cmn_bp = sorted(cmn_bp, key=lambda bp: bp.depth)
        # Get the bottom most blueprint, which is the best ancestor for both of these in the tree.
        blueprint_to_use = cmn_bp[-1]

        return blueprint_to_use

    @abc.abstractmethod
    def match(self, route: str, method: str) -> typing.Tuple[ABCRoute, typing.Iterable]:
        """
        Matches a route.

        :param route: The route path to match.
        :param method: The method of the route.

        :returns: A two-item tuple:
            The route that was matched,
            An iterable of items to be passed to invoke. This can be any iterable - the route invoke method must
            handle it appropriately.

        :raises: :class:`HTTPException` with 404 if the route was matched.
        :raises: :class:`HTTPException` with 405 if the route was matched but no methods matched.
        """
