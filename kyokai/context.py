"""
Stores HTTPRequestContext
"""
from asphalt.core import Context
from typeguard import check_argument_types

import kyokai


class HTTPRequestContext(Context):
    """
    Sub-class of context used for HTTP requests.
    """

    cfg = {}

    def __init__(self, request, parent: Context):
        assert check_argument_types()
        super().__init__(parent=parent)
        self._request = request

    @property
    def request(self) -> 'kyokai.Request':
        return self._request
