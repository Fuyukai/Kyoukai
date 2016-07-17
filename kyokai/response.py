"""
Module for a Response object.

A Response is returned by Routes when the underlying coroutine is done.
"""
import warnings

try:
    from http_parser.parser import IOrderedDict
except ImportError:
    from http_parser.pyparser import IOrderedDict

    warnings.warn("Using fallback Python HTTP parser - this will negatively affect performance.")

from .util import HTTP_CODES, VERSION
import magic

from email.utils import formatdate
from http.cookies import SimpleCookie


class Response(object):
    """
    A response is responsible (no pun intended) for delivering data to the client, again.

    The method `to_bytes()` transforms this into a bytes response.
    """

    def __init__(self, code: int, body: str, headers: dict = None):
        """
        Create a new response.
        """
        self.code = code
        self.cookies = SimpleCookie()
        self.body = str(body)
        self.headers = IOrderedDict(headers) if headers else IOrderedDict()

    def _mimetype(self, body):
        """
        Calculates the mime type of the file.
        """
        mime = magic.from_buffer(body)
        if mime:
            return mime.decode() if isinstance(mime, bytes) else mime

    def _recalculate_headers(self):
        """
        Override certain headers, like Content-Size.
        """
        self.headers["Content-Length"] = len(self.body)
        if 'Content-Type' not in self.headers:
            self.headers["Content-Type"] = self._mimetype(self.body) or "text/plain"
        # Set cookies.
        self.headers["Date"] = formatdate()
        self.headers["Server"] = "Kyoukai/{} (see https://github.com/SunDwarf/Kyoukai)".format(VERSION)

    def to_bytes(self):
        """
        Return the correct response.
        """
        self._recalculate_headers()
        fmt = "HTTP/1.1 {code} {msg}\r\n{headers}{cookies}\r\n{body}\r\n"
        headers_fmt = ""
        # Calculate headers
        for name, val in self.headers.items():
            headers_fmt += "{}: {}\r\n".format(name, val)
        built = fmt.format(code=self.code, msg=HTTP_CODES.get(self.code, "Unknown"), headers=headers_fmt,
                           body=self.body, cookies=self.cookies.output() if len(self.cookies) else "")

        return built.encode()


def redirect(location, code=302, response_cls=Response):
    """
    Creates a redirect response.
    """
    # https://github.com/pallets/werkzeug/blob/master/werkzeug/utils.py#L373
    # response body used from Werkzeug
    res = response_cls(
        code=302,
        body=
        '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">\n'
        '<title>Redirecting...</title>\n'
        '<h1>Redirecting...</h1>\n'
        '<p>You should be redirected automatically to target URL: '
        '<a href="{location}">{location}</a>.  If not click the link.'.format(location=location),
        headers={"Location": location}
    )
    return res
