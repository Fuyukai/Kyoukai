"""
Module for a Response object.

A Response is returned by Routes when the underlying coroutine is done.
"""
import gzip
import warnings

import sys

try:
    from http_parser.parser import IOrderedDict
except ImportError:
    from http_parser.pyparser import IOrderedDict

    warnings.warn("Using fallback Python HTTP parser - this will negatively affect performance.")

from . import util
try:
    import magic
except (ImportError, OSError):
    _has_magic = False
    warnings.warn("Cannot load libmagic - Cannot determine file types automatically...")
else:
    _has_magic = True

from email.utils import formatdate
from http.cookies import SimpleCookie
import urllib.parse as uparse


class Response(object):
    """
    A response is responsible (no pun intended) for delivering data to the client, again.

    The method :meth:`to_bytes` transforms this into a bytes response.
    """

    def __init__(self, code: int, body: str, headers: dict = None):
        """
        Create a new response.
        """
        self.code = code
        self.cookies = SimpleCookie()
        self.body = str(body)
        self.headers = IOrderedDict(headers) if headers else IOrderedDict()

        self._should_gzip = False

    @property
    def gzip(self):
        """
        :return: If the request is to be gzip compressed.
        """
        return self._should_gzip

    @gzip.setter
    def gzip(self, value):
        self._should_gzip = value

    def _mimetype(self, body):
        """
        Calculates the mime type of the response, using libmagic.

        This is an **internal method**.
        """
        if _has_magic:
            mime = magic.from_buffer(body)
            if mime:
                return mime.decode() if isinstance(mime, bytes) else mime
            else:
                return "empty"
        else:
            return "text/plain"

    def _recalculate_headers(self):
        """
        Override certain headers, like Content-Size.

        This is an **internal method**.
        """
        self.headers["Content-Length"] = len(self.body)
        if 'Content-Type' not in self.headers:
            self.headers["Content-Type"] = self._mimetype(self.body) or "text/plain"

        # If it's gzip enabled, add the gzip header.
        if self._should_gzip:
            self.headers["Content-Encoding"] = "gzip"

        # Set cookies.
        self.headers["Date"] = formatdate()
        self.headers["Server"] = "Kyoukai/{} (see https://github.com/SunDwarf/Kyoukai)".format(util.VERSION)
        self.headers["X-Powered-By"] = "Kyoukai/{} on Python {}".format(util.VERSION,
                                                                        '.'.join(map(str, sys.version_info[0:2])))

    def to_bytes(self):
        """
        Serialize a Response into :class:`bytes` to return and send to the client.

        :return: The encoded data for the response.
        """
        self._recalculate_headers()

        if self.gzip:
            self.body = gzip.compress(self.body.encode(), 5)
            # Re-calculate content-length.
            self.headers["Content-Length"] = len(self.body)
        else:
            self.body = self.body.encode()

        fmt = "HTTP/1.1 {code} {msg}\r\n{headers}{cookies}\r\n"
        headers_fmt = ""
        # Calculate headers
        for name, val in self.headers.items():
            headers_fmt += "{}: {}\r\n".format(name, val)
        built = fmt.format(code=self.code, msg=util.HTTP_CODES.get(self.code, "Unknown"), headers=headers_fmt,
                           cookies=(self.cookies.output() + "\r\n") if len(self.cookies) else "")

        # Encode the built string so far.
        built = built.encode()

        # Append the body, plus the terminator.
        built += self.body + b"\r\n"

        return built

    @classmethod
    def redirect(cls, location, code=302):
        """
        Creates a new Response that redirects to a specific location.

        :param location: The location to redirect to.
        :param code: The code (usually a 301 or 302) to add to the response.
        :return: A new :class:`Response` for the redirect.
        """
        # https://github.com/pallets/werkzeug/blob/master/werkzeug/utils.py#L373
        # response body used from Werkzeug
        location = uparse.quote(location)

        res = cls(
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
