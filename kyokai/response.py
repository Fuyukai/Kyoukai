"""
Module for a Response object.

A Response is returned by Routes when the underlying coroutine is done.
"""
from http_parser.util import IOrderedDict

from .util import HTTP_CODES


class Response(object):
    """
    A response is responsible (no pun intended) for delivering data to the client, again.

    The method `to_bytes()` transforms this into a bytes response.
    """

    def __init__(self, code: int, body: str, headers: dict):
        """
        Create a new response.
        """
        self.code = code
        self.body = str(body)
        self.headers = IOrderedDict(headers)

    def _recalculate_headers(self):
        """
        Override certain headers, like Content-Size.
        """
        self.headers["Content-Length"] = len(self.body)
        if 'Content-Type' not in self.headers:
            self.headers["Content-Type"] = "text/plain"

    def to_bytes(self):
        """
        Return the correct response.
        """
        self._recalculate_headers()
        fmt = "HTTP/1.1 {code} {msg}\r\n{headers}\r\n{body}\r\n"
        headers_fmt = ""
        # Calculate headers
        for name, val in self.headers.items():
            headers_fmt += "{}: {}\r\n".format(name, val)
        built = fmt.format(code=self.code, msg=HTTP_CODES.get(self.code, "Unknown"), headers=headers_fmt,
                           body=self.body)

        return built.encode()
