"""
Route groups are classes that allow you to group a set of routes together.

.. currentmodule:: kyoukai.routegroup
"""
import collections
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
                    rtt.routes = func.routes
                    rtt.bp = bp

                    # copy hooks
                    for type_, hooks in func.route_hooks.items():
                        for hook in hooks:
                            rtt.add_hook(type_, hook)

                    bp.routes.append(rtt)
                elif func.rg_delegate == "errorhandler":
                    # add the error handler using `errorhandler_code`
                    for code in func.errorhandler_codes:
                        bp.add_errorhandler(value, code)
                elif func.rg_delegate == "hook":
                    # add the hook
                    bp.add_hook(func.hook_type, value)

        setattr(obb, "_{.__name__}__blueprint".format(self), bp)

    def __call__(self, *args, **kwargs):
        obb = object.__new__(self)
        obb.__init__(*args, **kwargs)
        self._init_blueprint(obb)
        return obb


def route(url: str, methods: typing.Iterable[str] = ("GET", "HEAD"), **kwargs):
    """
    A companion function to the RouteGroup class. This follows :meth:`.Blueprint.route` in 
    terms of arguments, and marks a function as a route inside the class.
    
    This will return the original function, with some attributes attached:
    
        - ``in_group``: Marks the function as in the route group.
        - ``rg_delegate``: Internal. The type of function inside the group this is.
        - ``route_kwargs``: Keyword arguments to provide to ``wrap_route``.
        - ``route_url``: The routing URL to provide to ``add_route``.
        - ``route_methods``: The methods for the route.
        - ``route_hooks``: A defaultdict of route-specific hooks.
        
    Additionally, the following methods are added.
    
        - ``hook``: A decorator that adds a hook of type ``type_``.
        - ``before_request``: A decorator that adds a ``pre`` hook.
        - ``after_request``: A decorator that adds a ``post`` hook.
    
    .. versionadded:: 2.1.1
    
    .. versionchanged:: 2.1.3
    
        Added the ability to add route-specific hooks.
        
    .. versionchanged:: 2.2.0
        
        Now accepts an already edited function as the function to decorate - this will add a new \
        routing url and method pair to the :attr:`.Route.routes`.

    .. versionchanged:: 2.2.2

        Default methods changed to GET and HEAD.
    
    :param url: The routing URL of the route.
    :param methods: An iterable of methods for the route.
    """

    def inner(func):
        # add the required attrs which are used on a scan later
        func.in_group = True
        func.rg_delegate = "route"
        func.route_kwargs = kwargs

        # try and append to the routes
        # failing that, create a new list
        try:
            func.routes.append((url, methods))
        except AttributeError:
            func.routes = [(url, methods)]

        if not hasattr(func, "route_hooks"):
            func.route_hooks = collections.defaultdict(lambda: [])

            # helper for route-specific hooks.
            def hook(type_: str):
                def _inner2(hookfunc):
                    func.route_hooks[type_].append(hookfunc)
                    return hookfunc

                return _inner2

            func.hook = hook
            func.before_request = hook("pre")
            func.after_request = hook("post")

        return func

    return inner


def errorhandler(startcode: int, endcode: int = None, step: int = None):
    """
    A companion function to the RouteGroup class. This follows :meth:`.Blueprint.errorhandler` in 
    terms of arguments. 
    
    :param startcode: The error code to handle, for example 404.
        This also represents the start of an error range, if endcode is not None.
    :param endcode: The end of the error code range to handle. Error handlers will be added
        for all requests between startcode and endcode.
    :param step: The step for the error handler range.
    """

    def inner(func):
        func.in_group = True
        func.rg_delegate = "errorhandler"

        # less code here
        if endcode is None:
            codes = [startcode]
        else:
            codes = range(startcode, endcode, step or 1)

        for code in codes:
            try:
                func.errorhandler_codes.append(code)
            except AttributeError:
                func.errorhandler_codes = [code]

        return func

    return inner

# hooks


def hook(type_: str):
    """
    Marks a function as a hook.
    
    :param type_: The type of hook to mark. 
    """

    def inner(func):
        func.in_group = True
        func.rg_delegate = "hook"
        func.hook_type = type_

        return func

    return inner


def before_request(func):
    """
    Helper decorator to mark a function as a pre-request hook. 
    """
    return hook("pre")(func)


def after_request(func):
    """
    Helper decorator to mark a function as a post-request hook. 
    """
    return hook("post")(func)


class RouteGroup(object, metaclass=RouteGroupType):
    """
    A route group is a class that contains multiple methods that are decorated with the route 
    decorator. They produce a blueprint that can be added to the tree that includes all methods 
    in the route group.
     
    .. code-block:: python
    
        class MyGroup(RouteGroup, prefix="/api/v1"):
            def __init__(self, something: str):
                self.something = something
                
            @route("/ping")
            async def ping(self, ctx: HTTPRequestContext):
                return '{"response": self.something}'
                
    Blueprint parameters can be passed in the class call.
    
    To add the route group as a blueprint, use 
    :meth:`.Blueprint.add_route_group(MyGroup, *args, **kwargs)`.
    """
