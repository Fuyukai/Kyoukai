"""
Stores HTTPRequestContext
"""
from asphalt.core import Context
from typeguard import check_argument_types


class HTTPRequestContext(Context):
    """
    Sub-class of context used for HTTP requests.
    """

    def __init__(self, request, parent: Context):
        assert check_argument_types()
        super().__init__(parent=parent)
        self.request = request
