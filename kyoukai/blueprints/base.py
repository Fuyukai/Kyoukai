"""
The ABC for a Kyoukai Blueprint.

All Blueprint classes should be derived from this class.
"""
import abc


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

    @abc.abstractmethod
    def add_child(self, child: 'ABCBlueprint'):
        """
        Add a child Blueprint to the current blueprint.

        .. warning::
            This will override the parent of the blueprint, replacing it with this one.

        :param child: The child blueprint.
        """

    @abc.abstractmethod
    def gather_routes(self) -> list:
        """
        Gathers a list of routes from all children.
        :return: A list of route objects.
        """

    @abc.abstractmethod
    def match(self, route: str, method: str = None):
        """
        Matches a route inside the blueprint.

        Often, this just delegates to the Router to route.

        :param route: The route to match, e.g ``/abc/def``.
        :param method: The method of the route.

        :raises: A :class:`kyoukai.exc.HTTPException` with code 415 if the method is not valid.
        :returns: The :class:`Route` if the route was matched, or None.
        """
