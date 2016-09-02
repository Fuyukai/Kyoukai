"""
Stores HTTPRequestContext
"""
from asphalt.core import Context
from typeguard import check_argument_types

import kyoukai


class HTTPRequestContext(Context):
    """
    Sub-class of context used for HTTP requests.
    """

    cfg = {}

    def __init__(self, request, app, parent: Context):
        assert check_argument_types()
        super().__init__(parent=parent)
        self._request = request

        self._app = app

        # These are filled in by the app.
        self.blueprint = None  # type: 'kyoukai.Blueprint'
        self.route = None  # type: 'kyoukai.Route'

    # Various properties, to make request access easier for IDEs.

    @property
    def request(self) -> 'kyoukai.Request':
        return self._request

    @request.setter
    def request(self, req: 'kyoukai.Request'):
        self._request = req

    @property
    def app(self) -> 'kyoukai.Kyoukai':
        return self._app
