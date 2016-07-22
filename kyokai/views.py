"""
Allows making a class of views.
"""
import weakref

from kyokai.route import Route


def route(regex, methods: list = None, hard_match: bool = False):
    """
    Create a "bound" route.

    This should then be updated by ViewMeta with the correct self param, and added to the blueprint with the
    Blueprint.bind_view() method.
    """
    if not methods:
        methods = ["GET"]
    return Route(None, regex, methods, hard_match=hard_match, bound=True)


class ViewMeta(type):
    """
    Defines a way to automatically update routes.
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
        return [i for i in cls.__dict__.values() if isinstance(i, Route)]


class View(metaclass=ViewMeta):
    """
    Stub class to allow inheriting from easily without having to do metaclass=ViewMeta.
    """
