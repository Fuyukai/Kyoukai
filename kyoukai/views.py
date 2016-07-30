"""
Views are like grouped together routes - but not Blueprints. They allow creating classes for routes, and storing
data, etc inside the class.

This is similar to FlaskViews
"""
import weakref

from kyoukai.route import Route


def route(regex, methods: list = None):
    """
    Create a "bound" route.

    This should then be updated by ViewMeta with the correct self param, and added to the blueprint with the
    Blueprint.bind_view() method.

    This route is meant to be placed in a class that inherits from :class:`View`.
    """
    if not methods:
        methods = ["GET"]
    return Route(None, regex, methods, bound=True)


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
        return [i for i in cls.__dict__.values() if isinstance(i, Route)]


class View(metaclass=ViewMeta):
    """
    Stub class to allow inheriting from easily without having to do metaclass=ViewMeta.
    """
