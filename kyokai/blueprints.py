"""
Kyōkai are simply groups of routes.

They're a simpler way of grouping your routes together instead of having to import your app object manually all of
the time.
"""
from kyokai.route import Route


class Blueprint(object):
    """
    A Blueprint contains one public method: `bp.route`. It acts exactly the same as a normal route method.

    If you set a `url_prefix` in the constructor, this prefix will be added onto your routes.
    """
    def __init__(self, name: str, url_prefix: str=""):
        self._prefix = url_prefix
        self._name = name

        self.routes = []

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
        r = Route(regex, methods, hard_match)
        self.routes.append(r)
        return r

    def _init_bp(self):
        return self.routes