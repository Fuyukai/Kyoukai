"""
Views are like grouped together routes - but not Blueprints. They allow creating classes for routes, and storing
data, etc inside the class.
"""
from kyoukai.route import Route


def route(regex, methods: list = None, route_cls: type=Route):
    """
    Create a "bound" route.

    This should then be updated by ViewMeta with the correct self param, and added to the blueprint with the
    Blueprint.bind_view() method.

    This route is meant to be placed in a class that inherits from :class:`View`.

    .. versionchanged:: 1.8

        This method now accepts an optional ``route_cls`` which designates which Route class to wrap the coroutines in.

    :param regex: The regex to use for routing.

    :param methods: The methods that are allowed for this route.

    :param route_cls: The Route class to wrap this Route in.

    :return: The :class:`Route` that wraps this coroutine.
    """
    if not methods:
        methods = ["GET"]

    def _route_inner(coro):
        new_route = route_cls(None, regex, methods, bound=True)
        new_route.create(coro)
        return new_route

    return _route_inner


class ViewMeta(type):
    """
    Defines a way to automatically update routes.

    Internal metaclass.
    """
    __registry = {}

    def __call__(cls, *args, **kwargs):
        """
        Establish a singleton class, and update Route objects as appropriate.
        """
        name = cls.__name__
        if name in ViewMeta.__registry:
            return ViewMeta.__registry[name]

        new_class = super().__call__(*args, **kwargs)

        # Give the new_class a `_binded` property.
        # Used for the Blueprint.
        new_class._binded = False

        # Loop over the cls' dict.
        for item in cls.__dict__.values():
            if isinstance(item, Route):
                # New Route item.
                if item._bound:
                    item.self = new_class

        ViewMeta.__registry[name] = new_class

        return new_class

    def get_routes(cls):
        """
        :return: A list of Route objects for the specified View.
        """
        return [i for i in cls.__dict__.values() if isinstance(i, Route)]


class View(metaclass=ViewMeta):
    """
    Stub class to allow inheriting from easily without having to do metaclass=ViewMeta.
    """
