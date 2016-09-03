"""
Defines the ABC for a router.
"""

import abc

import kyoukai.app


class ABCRouter(abc.ABC):
    """
    A router defines how routes are routed from an incoming client connection.

    Before 1.10, routes were purely routed based on a regular expression. In 1.10 and above, the Router is
    responsible for routing, which (by default) is a regular expression but can be extended to use something like the
    Werkzeug router.
    """
    def __init__(self, app: 'kyoukai.app.Kyoukai'):
        self.app = app

    @abc.abstractmethod
    def match(self, route: str, method: str):
        """
        Matches a route.

        :param route: The route path to match.
        :param method: The method of the route.

        :return: The route object matched.
        :raises: :class:`HTTPException` with 404 if the route was matched.
        :raises: :class:`HTTPException` with 405 if the route was matched but no methods matched.
        """

