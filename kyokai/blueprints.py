"""
Kyōkai blueprints are simply groups of routes.

They're a simpler way of grouping your routes together instead of having to import your app object manually all of
the time.
"""
from kyokai.route import Route


class Blueprint(object):
    """
    A Blueprint is a container for routes.

    Blueprints have 'parent' blueprints - they inherit error handlers and hooks from them. The root blueprint has no
    parent, so it does not inherit from anything.

    Note that if a Blueprint that is not the root blueprint has a parent value of None, it is automatically set to
    inherit the root blueprint of the app.
    """
    def __init__(self, name: str, parent: 'Blueprint'=None,
                 url_prefix: str=""):
        self._prefix = url_prefix
        self._name = name

        self.routes = []

        self.errhandlers = {}

        self._parent = parent

    @property
    def parent(self) -> 'Blueprint':
        """
        Returns the parent Blueprint of the currentl Blueprint.
        """
        return self._parent

    @parent.setter
    def parent(self, bp: 'Blueprint'):
        """
        Sets the parent blueprint.
        """
        self._parent = bp

    def route(self, regex, methods: list = None, hard_match: bool = False):
        """
        Create an incoming route for a function.

        Parameters:
            regex:
                The regular expression to match the path to.
                In standard Python `re` forme.

                Group matches are automatically extracted from the regex, and passed as arguments.

            methods:
                The list of allowed methods, e.g ["GET", "POST"].
                You can check the method with `request.method`.

            hard_match:
                Should we match based on equality, rather than regex?

                This prevents index or lower level paths from matching 404s at higher levels.
        """
        if not methods:
            methods = ["GET"]
        # Override hard match if it's a `/` route.
        if regex == "/":
            hard_match = True
        regex = self._prefix + regex
        r = Route(self, regex, methods, hard_match)
        self.routes.append(r)
        return r

    def errorhandler(self, code: int):
        """
        Create an error handler for the specified code.

        This will wrap the function in a Route.
        """
        r = Route(self, "", [])
        self.errhandlers[code] = r
        return r
