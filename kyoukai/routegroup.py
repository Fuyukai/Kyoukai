"""
Route groups are classes that allow you to group a set of routes together.

.. currentmodule:: kyoukai.routegroup
"""
import inspect
import typing


def get_rg_bp(group: 'RouteGroup'):
    """
    Gets the :class:`~.Blueprint` created from a :class:`~.RouteGroup`.
    """
    return getattr(group, "_{0.__name__}__blueprint".format(type(group)))


class RouteGroupType(type):
    """
    The metaclass for a route group.
    
    This is responsible for passing the keyword arguments to the metaclass.
    """

    def __new__(mcs, name, bases, class_body, **kwargs):
        """
        Override of `__new__` to ensure the __init__ signature is compatible.
        """
        return super().__new__(mcs, name, bases, class_body)

    def __init__(self, name, bases, class_body, **kwargs):
        """
        Override of `__init__` to store the blueprint params.
        """
        super().__init__(name, bases, class_body)
        self._bp_kwargs = kwargs

    def _init_blueprint(self, obb):
        """
        Initializes the Blueprint used by this route group.
        
        :param obb: The route group instance to intialize. 
        """
        # circular imports tm
        from kyoukai.blueprint import Blueprint
        bp = Blueprint(self.__name__, **self._bp_kwargs)
        # get all the method types that have a `.route` attr on them
        for name, value in inspect.getmembers(obb):
            # unwrap methods
            if not hasattr(value, "__func__"):
                continue

            func = value.__func__
            if getattr(func, "in_group", False) is True:
                # check the delegate type
                if func.rg_delegate == "route":
                    # wrap value, but use func attrs
                    # this preserves the method and `self`
                    rtt = bp.wrap_route(value, **func.route_kwargs)
                    bp.add_route(rtt, value.route_url, func.route_methods)
                elif func.rg_delegate == "errorhandler":
                    # add the error handler using `errorhandler_code`
                    bp.add_errorhandler(value, func.errorhandler_code)

        setattr(obb, "_{.__name__}__blueprint".format(self), bp)

    def __call__(self, *args, **kwargs):
        obb = object.__new__(self)
        obb.__init__(*args, **kwargs)
        self._init_blueprint(obb)
        return obb


def route(url: str, methods: typing.Iterable[str] = ("GET",), **kwargs):
    """
    A companion function to the RouteGroup class. This follows :meth:`.Blueprint.route` in 
    terms of arguments, and marks a function as a route inside the class.
    
    :param url: The routing URL of the route.
    :param methods: An iterable of methods for the route.
    """

    def inner(func):
        # add the required attrs which are used on a scan later
        func.in_group = True
        func.rg_delegate = "route"
        func.route_kwargs = kwargs
        func.route_url = url
        func.route_methods = methods

        return func

    return inner


def errorhandler(code: int):
    """
    A companion function to the RouteGroup class. This follows :meth:`.Blueprint.errorhandler` in 
    terms of arguments. 
    
    :param code: The code for the error handler.
    """
    def inner(func):
        func.in_group = True
        func.rg_delegate = "errorhandler"
        func.errorhandler_code = code

        return func

    return inner


class RouteGroup(object, metaclass=RouteGroupType):
    """
    A route group is a class that contains multiple methods that are decorated with the route 
    decorator. They produce a blueprint that can be added to the tree that includes all methods 
    in the route group.
     
    .. code-block:: python
    
        class MyGroup(RouteGroup, url_prefix="/api/v1"):
            def __init__(self, something: str):
                self.something = something
                
            @route("/ping")
            async def ping(self, ctx: HTTPRequestContext):
                return '{"response": self.something}'
                
    Blueprint parameters can be passed in the class call.
    
    To add the route group as a blueprint, use 
    :meth:`.Blueprint.add_route_group(MyGroup, *args, **kwargs)`.
    """
