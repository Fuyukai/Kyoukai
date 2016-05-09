"""
A request represents a client wanting to get a resource from the server.

This is automatically passed into your app route when an appropriate path is recieved.
"""

# Use the C parser if applicable.
try:
    from http_parser.parser import HttpParser
except ImportError:
    from http_parser.pyparser import HttpParser

from kyokai.exc import HTTPClientException


class Request(object):
    """
    A Request object.

    This should not be manually created. Instead, it is automatically provided by Kyokai.

    Attributes:
        method: str
            The method of the request.
    """

    def __init__(self, parser: HttpParser):
        """
        Create a new Request.
        """
        self._parser = parser
        self.method = parser.get_method()
        self.path = parser.get_path()
        self.headers = parser.get_headers()

    @classmethod
    def from_data(cls, data: bytes):
        """
        Create a new request from request data.
        """
        parser = HttpParser()
        # Get the length of the data.
        data_len = len(data)
        # Execute the parser.
        parsed_len = parser.execute(data, data_len)
        if data_len != parsed_len:
            raise HTTPClientException(400, "Bad Request")

        # Create a new request.
        req = cls(parser)

        return req