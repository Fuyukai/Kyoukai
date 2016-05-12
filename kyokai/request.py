"""
A request represents a client wanting to get a resource from the server.

This is automatically passed into your app route when an appropriate path is recieved.
"""
import json
import logging
import urllib.parse as uparse

# Use the C parser if applicable.
from http import cookies

try:
    from http_parser.parser import HttpParser, IOrderedDict
except ImportError:
    from http_parser.pyparser import HttpParser, IOrderedDict

from kyokai.exc import HTTPClientException


class Request(object):
    """
    A Request object.

    This should not be manually created. Instead, it is automatically provided by Kyokai.

    Attributes:
        method: str
            The method of the request.
    """

    __slots__ = ["_parser", "method", "path", "headers", "query", "body", "raw_data", "source", "args",
                 "form", "values", "cookies", "extra", "json"]

    def __init__(self, parser: HttpParser):
        """
        Create a new Request.
        """
        self._parser = parser
        self.method = parser.get_method()
        self.path = parser.get_path()
        self.headers = parser.get_headers()
        self.query = parser.get_query_string()
        self.body = parser.recv_body().decode()

        self.cookies = cookies.SimpleCookie()
        self.cookies.load(self.headers.get("Cookie", "")) or {}

        self.raw_data = b""

        self.source = "0.0.0.0"

        # urlparse out the items.
        _raw_args = uparse.parse_qs(self.query, keep_blank_values=True)
        # Reparse args
        self.args = IOrderedDict()
        for k, v in _raw_args.items():
            if len(v) == 1:
                self.args[k] = v[0]
            elif len(v) == 0:
                self.args[k] = None
            else:
                self.args[k] = v
        if self.headers.get("Content-Type") == "application/json":
            # Parse as JSON
            self.form = json.loads(self.body)
        else:
            self.form = uparse.parse_qs(self.body, keep_blank_values=True)

        self.values = IOrderedDict(self.args)
        self.values.update(self.form if self.form else {})

    @property
    def fully_parsed(self):
        return self._parser.is_message_complete()

    @classmethod
    def from_data(cls, data: bytes, source: str):
        """
        Create a new request from request data.
        """
        parser = HttpParser()
        # Get the length of the data.
        data_len = len(data)
        # Execute the parser.
        parsed_len = parser.execute(data, data_len)
        if parsed_len == 0 or (data_len != parsed_len and parser.is_message_complete()):
            raise HTTPClientException(400, "Bad Request")

        # Create a new request.
        req = cls(parser)

        # Set the raw data.
        req.raw_data = data
        # Set the IP.
        req.source = source

        return req